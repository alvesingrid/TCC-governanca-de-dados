"""Piloto, etapa 3: inventário e cobertura de descrições do banco do MCID.

O que faz (somente leitura, não lê nenhuma linha de dado):
  1. Lista todas as tabelas e colunas dos schemas bronze, prata, ouro e seeds.
  2. Pega a estimativa de linhas de cada tabela (estatística do Postgres).
  3. Confere, para cada coluna, se ela tem descrição:
       - no dbt (arquivos .yml de models/, seeds/ e snapshots/), que é a
         documentação do projeto;
       - no próprio Postgres (comentário da coluna).
  4. Salva tudo em resultados/<data de hoje>/ neste repositório.

Como rodar (com a VPN ligada):
    uv run --project ~/TCC/data-application-cidades python scripts/piloto_inventario.py
"""

import csv
import datetime as dt
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from conexao import CIDADES_REPO, conectar, pasta_resultados  # noqa: E402
from dbt_docs import ler_documentacao_dbt  # noqa: E402

DBT = CIDADES_REPO / "dbt" / "mcid"
SCHEMAS = ["bronze", "prata", "ouro", "seeds"]

# Quando a tabela não está no dbt, o produto é deduzido pelo começo do nome.
PREFIXOS = [
    ("backup_", "(cópia de backup)"),
    ("prata_conjuntura_", "conjuntura"), ("ouro_conjuntura_", "conjuntura"),
    ("prata_far_historico_", "mcmv_historico"), ("prata_fds_historico_", "mcmv_historico"),
    ("prata_rural_historico_", "mcmv_historico"), ("bronze_dhist_", "mcmv_historico"),
    ("prata_far_", "far"), ("ouro_far_", "far"),
    ("prata_fds_", "fds"), ("ouro_fds_", "fds"),
    ("prata_rural_", "rural"), ("ouro_rural_", "rural"),
    ("prata_reforma_casa_brasil_", "reforma_casa_brasil"),
    ("ouro_reforma_casa_brasil_", "reforma_casa_brasil"),
    ("prata_linha_financiada_", "linha_financiada"), ("ouro_linha_financiada_", "linha_financiada"),
    ("bronze_sharepoint_", "linha_financiada"),
    ("bronze_abecip_", "conjuntura"), ("bronze_bacen_", "conjuntura"), ("bronze_fgv_", "conjuntura"),
    ("bronze_fipezap_", "conjuntura"), ("bronze_ibge_", "conjuntura"),
    ("bronze_infomoney_", "conjuntura"), ("bronze_novo_caged", "conjuntura"),
    ("bronze_cbic_", "conjuntura"), ("bronze_manual_", "conjuntura"), ("bronze_siafi_", "conjuntura"),
]

CONSULTA = """
SELECT n.nspname, cl.relname, cl.relkind, cl.reltuples,
       a.attname, col_description(cl.oid, a.attnum)
FROM pg_class cl
JOIN pg_namespace n ON n.oid = cl.relnamespace
JOIN pg_attribute a ON a.attrelid = cl.oid AND a.attnum > 0 AND NOT a.attisdropped
WHERE n.nspname = ANY(%s) AND cl.relkind IN ('r', 'v', 'm', 'p', 'f')
ORDER BY n.nspname, cl.relname, a.attnum;
"""
TIPOS = {"r": "tabela", "p": "tabela", "v": "view", "m": "view materializada", "f": "externa"}


def produto_por_prefixo(nome: str) -> str:
    for prefixo, produto in PREFIXOS:
        if nome.startswith(prefixo):
            return produto
    return "(não identificado)"


def montar_inventario(linhas_banco, docs):
    """Junta o que veio do banco com o que está no dbt."""
    tabelas, colunas = {}, []
    for schema, tabela, kind, reltuples, coluna, comentario in linhas_banco:
        chave = (schema, tabela)
        doc = docs.get(tabela.lower())
        if chave not in tabelas:
            tabelas[chave] = {
                "schema": schema, "tabela": tabela, "tipo": TIPOS.get(kind, kind),
                "produto": doc["produto"] if doc else produto_por_prefixo(tabela),
                "no_dbt": bool(doc),
                "tabela_descrita_dbt": bool(doc and doc["descricao_ok"]),
                "linhas_estimadas": int(reltuples) if reltuples is not None and reltuples >= 0 else "",
                "colunas": 0, "colunas_descritas_dbt": 0, "colunas_comentario_pg": 0,
            }
        t = tabelas[chave]
        descrita = bool(doc and doc["colunas"].get(coluna.lower(), False))
        tem_comentario = bool(comentario and comentario.strip())
        t["colunas"] += 1
        t["colunas_descritas_dbt"] += descrita
        t["colunas_comentario_pg"] += tem_comentario
        colunas.append({
            "schema": schema, "tabela": tabela, "produto": t["produto"], "coluna": coluna,
            "descrita_dbt": int(descrita), "comentario_pg": int(tem_comentario),
        })
    return list(tabelas.values()), colunas


def resumir(tabelas, chave):
    grupos = defaultdict(lambda: {"tabelas": 0, "no_dbt": 0, "colunas": 0, "descritas": 0, "pg": 0})
    for t in tabelas:
        g = grupos[t[chave]]
        g["tabelas"] += 1
        g["no_dbt"] += t["no_dbt"]
        g["colunas"] += t["colunas"]
        g["descritas"] += t["colunas_descritas_dbt"]
        g["pg"] += t["colunas_comentario_pg"]
    return dict(sorted(grupos.items()))


def formatar_resumo(tabelas, data):
    def pct(a, b):
        return f"{100 * a / b:.1f}%" if b else "-"

    linhas = [f"Piloto - inventário do banco cidades (cópia de {data})", ""]
    for titulo, chave in [("POR CAMADA", "schema"), ("POR PRODUTO", "produto")]:
        linhas.append(titulo)
        linhas.append(f"{'grupo':<24}{'tabelas':>8}{'no dbt':>8}{'colunas':>9}"
                      f"{'descr. dbt':>12}{'%':>8}{'coment. pg':>12}")
        total = {"tabelas": 0, "no_dbt": 0, "colunas": 0, "descritas": 0, "pg": 0}
        for nome, g in resumir(tabelas, chave).items():
            for k in total:
                total[k] += g[k]
            linhas.append(f"{nome:<24}{g['tabelas']:>8}{g['no_dbt']:>8}{g['colunas']:>9}"
                          f"{g['descritas']:>12}{pct(g['descritas'], g['colunas']):>8}{g['pg']:>12}")
        linhas.append(f"{'TOTAL':<24}{total['tabelas']:>8}{total['no_dbt']:>8}{total['colunas']:>9}"
                      f"{total['descritas']:>12}{pct(total['descritas'], total['colunas']):>8}"
                      f"{total['pg']:>12}")
        linhas.append("")
    linhas.append("no dbt     = a tabela tem entrada em algum schema.yml do repositório")
    linhas.append("descr. dbt = colunas com descrição no schema.yml (sem TODO/TBD/'a definir')")
    linhas.append("coment. pg = colunas com comentário gravado no próprio Postgres")
    return "\n".join(linhas)


def salvar_csv(caminho, registros):
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(registros[0].keys()))
        w.writeheader()
        w.writerows(registros)


def main():
    data = dt.date.today().isoformat()
    docs = ler_documentacao_dbt(DBT)
    conn = conectar()
    with conn.cursor() as cur:
        cur.execute(CONSULTA, (SCHEMAS,))
        linhas_banco = cur.fetchall()
    conn.close()

    tabelas, colunas = montar_inventario(linhas_banco, docs)
    SAIDA = pasta_resultados()
    salvar_csv(SAIDA / f"inventario_tabelas_{data}.csv", tabelas)
    salvar_csv(SAIDA / f"inventario_colunas_{data}.csv", colunas)
    resumo = formatar_resumo(tabelas, data)
    (SAIDA / f"resumo_{data}.txt").write_text(resumo + "\n", encoding="utf-8")

    print(resumo)
    print(f"\nArquivos salvos em {SAIDA}")


if __name__ == "__main__":
    main()

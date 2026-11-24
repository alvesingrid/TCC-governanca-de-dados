"""Piloto: tamanho exato do recorte (Conjuntura, só fontes públicas).

Para cada tabela do recorte, nas camadas bronze e prata:
  - conta as linhas exatas (COUNT(*));
  - lista as colunas com o tipo de cada uma.
Somente leitura. Não mostra nenhum valor dos dados, só contagens e nomes.

Como rodar (com a VPN ligada):
    uv run --project ~/TCC/data-application-cidades python scripts/piloto_recorte.py
"""

import csv
import datetime as dt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from conexao import conectar, pasta_resultados  # noqa: E402


# Fontes públicas da Conjuntura. Ficam de fora: GEAVO/GEFUS (Caixa), SIAFI,
# CBIC, balanços de empresas e tudo que é digitado à mão (manual).
FONTES_PUBLICAS = ("abecip", "bacen", "fgv", "fipezap", "ibge", "infomoney", "novo_caged")
PREFIXOS = {
    "bronze": [f"bronze_{f}" for f in FONTES_PUBLICAS],
    "prata": [f"prata_conjuntura_{f}" for f in FONTES_PUBLICAS]
    + ["prata_conjuntura_pib_construcao_civil_pct"],  # derivada só do IBGE
}

COLUNAS_SQL = """
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema = %s
ORDER BY table_name, ordinal_position;
"""


def fonte_da_tabela(nome: str) -> str:
    for f in FONTES_PUBLICAS:
        if f"_{f}" in nome:
            return f
    return "ibge"


def main():
    data = dt.date.today().isoformat()
    conn = conectar()
    tabelas, colunas = [], []
    with conn.cursor() as cur:
        for schema, prefixos in PREFIXOS.items():
            cur.execute(COLUNAS_SQL, (schema,))
            por_tabela = {}
            for tabela, coluna, tipo in cur.fetchall():
                if any(tabela.startswith(p) for p in prefixos):
                    por_tabela.setdefault(tabela, []).append((coluna, tipo))
            for tabela in sorted(por_tabela):
                cur.execute(f'SELECT COUNT(*) FROM "{schema}"."{tabela}"')
                linhas = cur.fetchone()[0]
                tabelas.append({
                    "schema": schema, "tabela": tabela, "fonte": fonte_da_tabela(tabela),
                    "colunas": len(por_tabela[tabela]), "linhas": linhas,
                })
                for coluna, tipo in por_tabela[tabela]:
                    colunas.append({"schema": schema, "tabela": tabela, "coluna": coluna, "tipo": tipo})
    conn.close()

    SAIDA = pasta_resultados()
    for nome, registros in [("recorte_tabelas", tabelas), ("recorte_colunas", colunas)]:
        with open(SAIDA / f"{nome}_{data}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(registros[0].keys()))
            w.writeheader()
            w.writerows(registros)

    print(f"Recorte: Conjuntura, fontes públicas (cópia de {data})\n")
    print(f"{'schema':<8}{'tabela':<56}{'colunas':>8}{'linhas':>10}")
    for t in tabelas:
        print(f"{t['schema']:<8}{t['tabela']:<56}{t['colunas']:>8}{t['linhas']:>10}")
    for schema in PREFIXOS:
        ts = [t for t in tabelas if t["schema"] == schema]
        vazias = sum(1 for t in ts if t["linhas"] == 0)
        print(f"\nTOTAL {schema}: {len(ts)} tabelas, {sum(t['colunas'] for t in ts)} colunas, "
              f"{sum(t['linhas'] for t in ts)} linhas, {vazias} tabelas vazias")
    print(f"\nArquivos salvos em {SAIDA}")


if __name__ == "__main__":
    main()

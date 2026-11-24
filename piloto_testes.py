"""Piloto: um teste de qualidade por dimensão, com o Great Expectations.

Recorte: Conjuntura, fontes públicas, camada prata.
As quatro dimensões são as da Seção de qualidade do TCC:
completude, unicidade, validade e consistência.

Somente leitura. O resultado mostra só contagens e percentuais,
nunca valores dos dados.

Como rodar (com a VPN ligada):
    cd ~/TCC/data-application-cidades
    uv run python ~/TCC/piloto/piloto_testes.py
"""

import contextlib
import csv
import datetime as dt
import io
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("TQDM_DISABLE", "1")  # esconde as barras de progresso do GX

import great_expectations as gx  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from conexao import conectar  # noqa: E402

SAIDA = Path("~/TCC/piloto/resultados").expanduser()

# Um teste por dimensão. "preparar" cria colunas auxiliares quando a regra
# compara colunas entre si (o GX compara coluna com coluna).
TESTES = [
    {
        "dimensao": "Completude",
        "regra": "O valor do PIB não pode estar vazio",
        "tabela": "prata.prata_conjuntura_ibge_pib_corrente",
        "coluna": "valor",
        "expectativa": lambda: gx.expectations.ExpectColumnValuesToNotBeNull(column="valor"),
    },
    {
        "dimensao": "Unicidade",
        "regra": "Cada mês (ano + mês) aparece uma vez só",
        "tabela": "prata.prata_conjuntura_novo_caged_total",
        "coluna": "ano, mes",
        "expectativa": lambda: gx.expectations.ExpectCompoundColumnsToBeUnique(
            column_list=["ano", "mes"]),
    },
    {
        "dimensao": "Validade",
        "regra": "O mês está entre 1 e 12",
        "tabela": "prata.prata_conjuntura_abecip_financiamentos",
        "coluna": "mes",
        "expectativa": lambda: gx.expectations.ExpectColumnValuesToBeBetween(
            column="mes", min_value=1, max_value=12),
    },
    {
        "dimensao": "Consistência",
        "regra": "Saldo de empregos = admitidos - desligados",
        "tabela": "prata.prata_conjuntura_novo_caged_total",
        "coluna": "saldo, admitidos, desligados",
        "preparar": lambda df: df.assign(
            saldo_calculado=(df["admitidos"] - df["desligados"]).astype(float),
            saldo_informado=df["saldo"].astype(float)),
        "expectativa": lambda: gx.expectations.ExpectColumnPairValuesToBeEqual(
            column_A="saldo_informado", column_B="saldo_calculado"),
    },
]


def ler_tabela(conn, nome: str) -> pd.DataFrame:
    schema, tabela = nome.split(".")
    with conn.cursor() as cur:
        cur.execute(f'SELECT * FROM "{schema}"."{tabela}"')
        nomes = [c[0] for c in cur.description]
        return pd.DataFrame(cur.fetchall(), columns=nomes)


def rodar_teste(contexto, teste, df) -> dict:
    if "preparar" in teste:
        df = teste["preparar"](df)
    nome = teste["dimensao"].lower()
    fonte = contexto.data_sources.add_pandas(name=f"fonte_{nome}")
    ativo = fonte.add_dataframe_asset(name=f"ativo_{nome}")
    lote = ativo.add_batch_definition_whole_dataframe(f"lote_{nome}")
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        r = lote.get_batch(batch_parameters={"dataframe": df}).validate(teste["expectativa"]())
    res = r.result or {}
    total = res.get("element_count", len(df))
    violam = res.get("unexpected_count", 0) or 0
    return {
        "dimensao": teste["dimensao"],
        "regra": teste["regra"],
        "tabela": teste["tabela"],
        "coluna": teste["coluna"],
        "resultado": "Aprovado" if r.success else "Reprovado",
        "linhas_testadas": total,
        "linhas_que_violam": violam,
        "pct_violam": round(100 * violam / total, 2) if total else 0.0,
    }


def main():
    data = dt.date.today().isoformat()
    conn = conectar()
    dados = {t["tabela"]: ler_tabela(conn, t["tabela"]) for t in TESTES}
    conn.close()

    contexto = gx.get_context(mode="ephemeral")
    resultados = [rodar_teste(contexto, t, dados[t["tabela"]]) for t in TESTES]

    SAIDA.mkdir(parents=True, exist_ok=True)
    with open(SAIDA / f"testes_{data}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(resultados[0].keys()))
        w.writeheader()
        w.writerows(resultados)
    (SAIDA / f"testes_{data}.json").write_text(
        json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Testes de qualidade - Conjuntura, camada prata (cópia de {data})\n")
    for r in resultados:
        print(f"{r['dimensao']}: {r['resultado']}")
        print(f"  regra:  {r['regra']}")
        print(f"  tabela: {r['tabela']} ({r['coluna']})")
        print(f"  linhas: {r['linhas_que_violam']} de {r['linhas_testadas']} violam a regra "
              f"({r['pct_violam']}%)\n")
    aprovados = sum(r["resultado"] == "Aprovado" for r in resultados)
    print(f"{aprovados} de {len(resultados)} testes aprovados.")
    print(f"Arquivos salvos em {SAIDA}")


if __name__ == "__main__":
    main()

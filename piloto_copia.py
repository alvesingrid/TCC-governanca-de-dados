"""Piloto, etapa 1: cópia datada do recorte (Conjuntura, só fontes públicas).

Salva cada tabela do recorte (bronze e prata) em CSV, numa pasta com a data
de hoje, e calcula o período coberto por cada tabela (primeira e última data).
Os dados são de fontes públicas, então a cópia pode ir para o repositório.

Como rodar (com a VPN ligada):
    cd ~/TCC/data-application-cidades
    uv run python ~/TCC/piloto/piloto_copia.py
"""

import csv
import datetime as dt
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from conexao import conectar  # noqa: E402
from piloto_recorte import COLUNAS_SQL, PREFIXOS  # noqa: E402

TIPOS_DATA = ("date", "timestamp without time zone", "timestamp with time zone")
COLUNAS_TECNICAS = ("dt_ingest", "_ingested_at", "criado_em")


def coluna_de_data(colunas):
    """Escolhe a coluna que diz a que período o dado se refere."""
    for nome, tipo in colunas:
        if tipo in TIPOS_DATA and nome not in COLUNAS_TECNICAS:
            return ("data", nome)
    nomes = [n for n, _ in colunas]
    if "ano" in nomes:
        return ("ano", "ano")
    return None


def main():
    data = dt.date.today().isoformat()
    pasta = Path(f"~/TCC/piloto/copia_{data}").expanduser()
    pasta.mkdir(parents=True, exist_ok=True)
    conn = conectar()
    periodos = []
    with conn.cursor() as cur:
        for schema, prefixos in PREFIXOS.items():
            cur.execute(COLUNAS_SQL, (schema,))
            por_tabela = {}
            for tabela, coluna, tipo in cur.fetchall():
                if any(tabela.startswith(p) for p in prefixos):
                    por_tabela.setdefault(tabela, []).append((coluna, tipo))
            for tabela in sorted(por_tabela):
                cur.execute(f'SELECT * FROM "{schema}"."{tabela}"')
                nomes = [c[0] for c in cur.description]
                with open(pasta / f"{schema}.{tabela}.csv", "w", newline="", encoding="utf-8") as f:
                    w = csv.writer(f)
                    w.writerow(nomes)
                    w.writerows(cur.fetchall())
                escolha = coluna_de_data(por_tabela[tabela])
                inicio = fim = ""
                if escolha:
                    _, col = escolha
                    cur.execute(f'SELECT MIN("{col}"), MAX("{col}") FROM "{schema}"."{tabela}"')
                    inicio, fim = cur.fetchone()
                periodos.append({
                    "schema": schema, "tabela": tabela,
                    "coluna_periodo": escolha[1] if escolha else "",
                    "inicio": inicio, "fim": fim,
                })
    conn.close()

    with open(pasta / "periodos.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(periodos[0].keys()))
        w.writeheader()
        w.writerows(periodos)

    print(f"Cópia do recorte salva em {pasta} ({len(periodos)} tabelas)\n")
    print(f"{'schema':<8}{'tabela':<56}{'início':>12}{'fim':>12}")
    anos = []
    for p in periodos:
        ini, fim = p["inicio"], p["fim"]
        print(f"{p['schema']:<8}{p['tabela']:<56}{str(ini)[:10]:>12}{str(fim)[:10]:>12}")
        for v in (ini, fim):
            if v not in ("", None):
                anos.append(int(str(v)[:4]))
    sem = [p["tabela"] for p in periodos if p["inicio"] in ("", None)]
    if anos:
        print(f"\nAnos cobertos pelo recorte: {min(anos)} a {max(anos)}")
    if sem:
        print(f"Tabelas sem coluna de período identificada: {', '.join(sem)}")


if __name__ == "__main__":
    main()

"""Piloto: conta as linhas de todas as tabelas do banco, por camada.

Somente leitura. Faz só COUNT(*), não lê nenhum valor dos dados.
Pode levar alguns minutos, porque algumas tabelas são grandes.

Como rodar (com a VPN ligada):
    uv run --project ~/TCC/data-application-cidades python scripts/piloto_linhas.py
"""

import csv
import datetime as dt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from conexao import conectar, pasta_resultados  # noqa: E402

SCHEMAS = {"bronze": "Bronze", "prata": "Prata", "ouro": "Ouro", "seeds": "Apoio"}

LISTA = """
SELECT n.nspname, c.relname
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = ANY(%s) AND c.relkind IN ('r', 'v', 'm', 'p', 'f')
ORDER BY n.nspname, c.relname;
"""


def main():
    data = dt.date.today()
    conn = conectar()
    linhas = []
    with conn.cursor() as cur:
        cur.execute(LISTA, (list(SCHEMAS),))
        tabelas = cur.fetchall()
        for i, (schema, tabela) in enumerate(tabelas, 1):
            print(f"\r{i}/{len(tabelas)} tabelas contadas", end="", flush=True)
            try:
                cur.execute(f'SELECT COUNT(*) FROM "{schema}"."{tabela}"')
                n = cur.fetchone()[0]
                erro = ""
            except Exception as e:  # uma view quebrada não para a contagem
                conn.rollback()
                n, erro = 0, str(e).splitlines()[0]
            linhas.append({"schema": schema, "tabela": tabela, "linhas": n, "erro": erro})
    conn.close()
    print()

    SAIDA = pasta_resultados(data)
    with open(SAIDA / f"linhas_{data.isoformat()}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["schema", "tabela", "linhas", "erro"])
        w.writeheader()
        w.writerows(linhas)

    def br(n):
        return f"{n:,}".replace(",", ".")

    print(f"\nLinhas por camada (contagem de {data.strftime('%d/%m/%Y')})")
    total = 0
    for schema, nome in SCHEMAS.items():
        soma = sum(r["linhas"] for r in linhas if r["schema"] == schema)
        total += soma
        print(f"  {nome:<7}{br(soma):>15}")
    print(f"  {'Total':<7}{br(total):>15}")
    com_erro = [r for r in linhas if r["erro"]]
    if com_erro:
        print(f"\n{len(com_erro)} tabelas não puderam ser contadas (veja a coluna 'erro' no CSV).")


if __name__ == "__main__":
    main()

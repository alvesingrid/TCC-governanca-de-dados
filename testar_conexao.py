"""Teste de conexão com o Postgres do MCID (somente leitura).

Lista os schemas do banco e quantas tabelas há em cada um.
Não lê nenhum dado das tabelas, só nomes e contagens.

Como rodar (a partir da pasta do repositório):
    cd ~/TCC/data-application-cidades
    uv run python ~/TCC/piloto/testar_conexao.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from conexao import conectar  # noqa: E402

conn = conectar()

with conn.cursor() as cur:
    cur.execute(
        """
        SELECT table_schema, COUNT(*) AS tabelas
        FROM information_schema.tables
        WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
        GROUP BY table_schema
        ORDER BY table_schema;
        """
    )
    print("Schema | Tabelas")
    for schema, total in cur.fetchall():
        print(f"{schema} | {total}")

conn.close()
print("\nConexão OK (somente leitura).")

"""Conexão somente leitura com o Postgres do MCID, usada por todos os scripts do piloto.

Host, porta, usuário e banco vêm do .env do repositório.
A senha é pedida na hora (não aparece na tela e não fica salva).
"""

import getpass
import os

import psycopg2
from dotenv import load_dotenv

load_dotenv(os.path.expanduser("~/TCC/data-application-cidades/.env"))


def conectar():
    host = os.environ["DB_DW_HOST_MCID"]
    port = os.environ["DB_DW_PORT_MCID"]
    user = os.environ["DB_DW_USER_MCID"]
    dbname = os.environ["DB_DW_DBNAME_MCID"]
    senha = getpass.getpass(f"Senha do usuário {user} no banco {dbname}: ")
    conn = psycopg2.connect(
        host=host, port=port, user=user, password=senha, dbname=dbname
    )
    conn.set_session(readonly=True)  # garante que nada é alterado no banco
    return conn

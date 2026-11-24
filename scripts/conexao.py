"""Configuração comum dos scripts do piloto.

- Conexão somente leitura com o banco do Ministério das Cidades no Gov Hub.
  Host, porta, usuário e banco vêm do .env do repositório data-application-cidades;
  a senha é pedida na hora e não fica salva.
- Caminhos: os resultados vão para a pasta resultados/<data>/ deste repositório.

Variáveis de ambiente opcionais:
  CIDADES_REPO  caminho do clone do data-application-cidades
                (padrão: ~/TCC/data-application-cidades)
"""

import datetime as dt
import getpass
import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parents[1]
CIDADES_REPO = Path(os.environ.get("CIDADES_REPO", "~/TCC/data-application-cidades")).expanduser()

load_dotenv(CIDADES_REPO / ".env")


def pasta_resultados(data: dt.date | None = None) -> Path:
    """Pasta resultados/AAAA-MM-DD/ deste repositório (criada se não existir)."""
    pasta = RAIZ / "resultados" / (data or dt.date.today()).isoformat()
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def conectar():
    host = os.environ["DB_DW_HOST_MCID"]
    port = os.environ["DB_DW_PORT_MCID"]
    user = os.environ["DB_DW_USER_MCID"]
    dbname = os.environ["DB_DW_DBNAME_MCID"]
    senha = getpass.getpass(f"Senha do usuário {user} no banco {dbname}: ")
    conn = psycopg2.connect(host=host, port=port, user=user, password=senha, dbname=dbname)
    conn.set_session(readonly=True)  # garante que nada é alterado no banco
    return conn

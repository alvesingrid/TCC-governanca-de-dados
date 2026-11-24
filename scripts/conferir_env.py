"""Confere as variáveis do banco MCID no .env SEM mostrar a senha.

Como rodar:
    uv run --project ~/TCC/data-application-cidades python scripts/conferir_env.py
"""

import os
from pathlib import Path

from dotenv import dotenv_values

ENV = Path(os.environ.get("CIDADES_REPO", "~/TCC/data-application-cidades")).expanduser() / ".env"
CAMPOS = [
    "DB_DW_HOST_MCID",
    "DB_DW_PORT_MCID",
    "DB_DW_USER_MCID",
    "DB_DW_PASSWORD_MCID",
    "DB_DW_DBNAME_MCID",
]

# 1. Linhas repetidas no arquivo (a última vence).
linhas = ENV.read_text(encoding="utf-8").splitlines()
for campo in CAMPOS:
    n = sum(1 for l in linhas if l.strip().startswith(campo + "="))
    if n != 1:
        print(f"ATENÇÃO: {campo} aparece {n} vezes no .env (deve aparecer 1).")

# 2. Como cada valor foi lido.
valores = dotenv_values(ENV)
for campo in CAMPOS:
    v = valores.get(campo)
    if v is None or v == "":
        print(f"{campo}: VAZIO")
        continue
    if campo == "DB_DW_PASSWORD_MCID":
        avisos = []
        if v != v.strip():
            avisos.append("tem espaço no começo ou no fim")
        if v[:1] in "\"'" or v[-1:] in "\"'":
            avisos.append("ficou com aspas dentro do valor")
        # Linha crua, para ver se um # cortou a senha.
        crua = next(l for l in linhas if l.strip().startswith(campo + "="))
        bruto = crua.split("=", 1)[1]
        if "#" in bruto and "#" not in v:
            avisos.append("tem # e foi cortada (coloque a senha entre aspas)")
        print(f"{campo}: {len(v)} caracteres"
              + (f"  -> {'; '.join(avisos)}" if avisos else "  (formato ok)"))
    else:
        print(f"{campo}: {v}")

# 3. Variável já definida no terminal tem prioridade sobre o .env.
for campo in CAMPOS:
    if campo in os.environ:
        print(f"ATENÇÃO: {campo} também está definida no terminal e ganha do .env.")

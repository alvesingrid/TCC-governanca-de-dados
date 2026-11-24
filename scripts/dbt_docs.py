"""Lê as descrições de tabelas e colunas escritas nos .yml do dbt.

Lê as três pastas onde o dbt documenta o que vira tabela no banco:
models/ (chave `models:`), seeds/ (chave `seeds:`) e snapshots/ (chave `snapshots:`).
"""

import re
from pathlib import Path

import yaml

PLACEHOLDER = re.compile(r"\b(todo|tbd|a definir|sem descri[cç][aã]o)\b", re.I)
PASTAS = [("models", "models"), ("seeds", "seeds"), ("snapshots", "snapshots")]


def descricao_valida(texto) -> bool:
    if not isinstance(texto, str):
        return False
    t = texto.strip()
    return bool(t) and not PLACEHOLDER.search(t)


def _produto(pasta: str, partes: tuple) -> str:
    if pasta == "seeds":
        return "seeds"
    if pasta == "snapshots":
        return "conjuntura"  # os snapshots são todos do boletim de conjuntura
    return partes[0].removesuffix("_dbt") if len(partes) > 1 else "(raiz)"


def ler_documentacao_dbt(dbt_dir: Path) -> dict:
    """Retorna {nome_tabela: {"produto", "arquivo", "descricao_ok", "colunas": {col: ok}}}."""
    docs = {}
    for pasta, chave in PASTAS:
        base = dbt_dir / pasta
        if not base.exists():
            continue
        for arq in sorted(list(base.rglob("*.yml")) + list(base.rglob("*.yaml"))):
            try:
                conteudo = yaml.safe_load(arq.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError:
                continue
            if not isinstance(conteudo, dict):
                continue
            produto = _produto(pasta, arq.relative_to(base).parts)
            for m in conteudo.get(chave) or []:
                if not isinstance(m, dict) or "name" not in m:
                    continue
                nome = (m.get("config") or {}).get("alias") or m["name"]
                colunas = {}
                for c in m.get("columns") or []:
                    if isinstance(c, dict) and "name" in c:
                        colunas[str(c["name"]).lower()] = descricao_valida(c.get("description"))
                docs[str(nome).lower()] = {
                    "produto": produto,
                    "arquivo": str(arq.relative_to(dbt_dir)),
                    "descricao_ok": descricao_valida(m.get("description")),
                    "colunas": colunas,
                }
    return docs

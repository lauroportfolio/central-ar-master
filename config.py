"""Configuração do app, lida do arquivo .env (python-dotenv).

DB_MODE     localdb (Windows, login do Windows) ou docker (usuário sa)
DB_NAME     nome do banco (padrão: CentralDeAr)
DB_PASSWORD senha do sa — usada só no modo docker
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PASTA_PROJETO = Path(__file__).parent

load_dotenv(PASTA_PROJETO / ".env")


def modo_conexao() -> str:
    return os.getenv("DB_MODE", "localdb").strip().lower()


def nome_banco() -> str:
    return os.getenv("DB_NAME", "CentralDeAr").strip()


def senha_banco() -> str:
    return os.getenv("DB_PASSWORD", "")

#!/usr/bin/env bash
# Central de Ar Ltda. — inicia o sistema no Linux/WSL.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -x .venv/bin/python ]; then
    echo "[1/3] Criando o ambiente Python do projeto (.venv)..."
    python3 -m venv .venv
fi

echo "[2/3] Conferindo as dependências..."
.venv/bin/python -m pip install --disable-pip-version-check -q -r requirements.txt

if [ ! -f .env ]; then
    cp .env.example .env
    echo "      Arquivo .env criado a partir do .env.example (ajuste DB_MODE/DB_PASSWORD)."
fi

echo "[3/3] Abrindo o sistema: http://localhost:8501  (Ctrl+C para encerrar)"
exec .venv/bin/python -m streamlit run app.py "$@"

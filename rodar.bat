@echo off
setlocal
cd /d "%~dp0"
title Central de Ar - Sistema de Vendas

echo ==================================================
echo    Central de Ar Ltda. - Sistema de Vendas
echo ==================================================
echo.

if exist ".venv\Scripts\python.exe" goto instalar

echo [1/3] Criando o ambiente Python do projeto (.venv)...
py -3.12 -m venv .venv >nul 2>&1
if not exist ".venv\Scripts\python.exe" python -m venv .venv
if not exist ".venv\Scripts\python.exe" (
    echo.
    echo ERRO: Python nao encontrado.
    echo Instale o Python 3.12 marcando a opcao "Add python.exe to PATH"
    echo e de dois cliques neste arquivo de novo. Veja o README.md.
    echo.
    pause
    exit /b 1
)

:instalar
echo [2/3] Conferindo as dependencias - na primeira vez demora alguns minutos...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt
if errorlevel 1 (
    echo.
    echo ERRO ao instalar as dependencias. Confira a conexao com a internet.
    echo.
    pause
    exit /b 1
)

if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo       Arquivo .env criado a partir do .env.example.
)

echo [3/3] Abrindo o sistema no navegador: http://localhost:8501
echo       Para encerrar o sistema, feche esta janela.
echo.
".venv\Scripts\python.exe" -m streamlit run app.py
pause

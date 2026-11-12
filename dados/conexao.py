"""Conexão com o SQL Server e execução de stored procedures.

Regra do projeto: a aplicação só executa STORED PROCEDURES (EXEC usp_...).
Nenhum SELECT/INSERT/UPDATE/DELETE em tabela é feito no Python.

Procedures com parâmetro OUTPUT: o pyodbc não lê OUTPUT diretamente, então
executamos um lote "DECLARE @id INT; EXEC usp_X ..., @id_x = @id OUTPUT; SELECT @id;"
e lemos o resultado do SELECT final.
"""

from __future__ import annotations

import re
from contextlib import contextmanager
from decimal import Decimal

import pandas as pd
import pyodbc

import config
from util.erros import ErroBanco

# ---------------------------------------------------------------------------
# Conexão
# ---------------------------------------------------------------------------


def _chaves(valor: str) -> str:
    """Protege valores da string de conexão (ex.: senha com ; ou })."""
    return "{" + valor.replace("}", "}}") + "}"


def _string_conexao() -> str:
    modo = config.modo_conexao()
    banco = config.nome_banco()

    if modo == "localdb":
        return (
            "DRIVER={ODBC Driver 18 for SQL Server};"
            r"SERVER=(localdb)\MSSQLLocalDB;"
            f"DATABASE={banco};"
            "Trusted_Connection=yes;TrustServerCertificate=yes;"
        )

    if modo == "docker":
        senha = config.senha_banco()
        if not senha or senha == "troque_aqui":
            raise ErroBanco("Defina a senha do usuario sa em DB_PASSWORD no arquivo .env.")
        return (
            "DRIVER={ODBC Driver 18 for SQL Server};"
            "SERVER=localhost,1433;UID=sa;"
            f"PWD={_chaves(senha)};"
            f"DATABASE={banco};"
            "TrustServerCertificate=yes;"
        )

    raise ErroBanco(f"DB_MODE invalido no .env: '{modo}'. Use 'localdb' ou 'docker'.")


def _mensagem_legivel(erro: pyodbc.Error) -> str:
    """Tira os prefixos do driver e devolve só a mensagem do SQL Server."""
    estado = erro.args[0] if erro.args else ""
    texto = erro.args[1] if len(erro.args) > 1 else str(erro)

    # Formato do driver: "[42000] [Microsoft][ODBC Driver 18 for SQL Server][SQL Server]Msg (50026) (SQLExecDirectW)"
    # Pode haver várias mensagens separadas por "; ". Fica só o texto de cada uma.
    mensagens = []
    for parte in texto.split("[SQL Server]")[1:]:
        parte = re.sub(r";\s*\[\w+\]\s*\[Microsoft\].*$", "", parte)  # prefixo da próxima mensagem
        parte = re.sub(r"\s*\(SQL\w+\)\s*$", "", parte)               # (SQLExecDirectW)
        parte = re.sub(r"\s*\(\d+\)\s*$", "", parte).strip()          # (50026)
        if parte and parte not in mensagens:
            mensagens.append(parte)
    mensagem = " ".join(mensagens) or texto

    if estado == "IM002" or "Data source name not found" in texto or "Can't open lib" in texto:
        return ("Driver ODBC nao encontrado. Instale o 'ODBC Driver 18 for SQL Server' "
                "(veja o README).")
    if "Could not find stored procedure" in texto:
        return (f"{mensagem} — rode os scripts sql/01_complemento.sql e sql/02_seed.sql "
                "no banco (veja o README).")
    if "Cannot open database" in texto:
        return (f"Banco '{config.nome_banco()}' nao encontrado. Confira DB_NAME no arquivo .env "
                "e se o script sql/00_schema_reconstruido.sql foi executado.")
    if estado in ("08001", "HYT00") or "Login timeout" in texto or "network-related" in texto:
        return ("Nao foi possivel conectar ao SQL Server. Confira se o servidor esta ligado "
                f"e o DB_MODE do .env (atual: '{config.modo_conexao()}').")
    if "UQ_CLIENTE_CPF_CNPJ" in texto:
        return "Ja existe um cliente com este CPF/CNPJ."
    return mensagem


@contextmanager
def _cursor():
    try:
        conexao = pyodbc.connect(_string_conexao(), autocommit=True, timeout=10)
    except pyodbc.Error as erro:
        raise ErroBanco(_mensagem_legivel(erro)) from erro
    cursor = conexao.cursor()
    try:
        yield cursor
    except pyodbc.Error as erro:
        raise ErroBanco(_mensagem_legivel(erro)) from erro
    finally:
        cursor.close()
        conexao.close()


# ---------------------------------------------------------------------------
# Execução de procedures
# ---------------------------------------------------------------------------

_NOME_VALIDO = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def parametro(v):
    """float -> Decimal (evita 0.1 virar 0.1000000001 no DECIMAL do banco)."""
    if isinstance(v, float):
        return Decimal(str(v))
    return v


def _montar_exec(procedure: str, params: dict) -> tuple[str, list]:
    for nome in (procedure, *params):
        if not _NOME_VALIDO.match(nome):
            raise ValueError(f"Nome invalido: {nome}")
    atribuicoes = ", ".join(f"@{nome} = ?" for nome in params)
    sql = f"EXEC {procedure} {atribuicoes}".rstrip()
    return sql, [parametro(v) for v in params.values()]


def _primeiro_resultado(cursor) -> pd.DataFrame:
    # Pula mensagens/contagens até chegar no primeiro SELECT
    while cursor.description is None:
        if not cursor.nextset():
            return pd.DataFrame()
    colunas = [c[0] for c in cursor.description]
    tipos = {c[0]: c[1] for c in cursor.description}
    linhas = [tuple(l) for l in cursor.fetchall()]
    # Consome o restante da resposta (mensagens, fim da procedure). Sem isso a
    # conexão volta "ocupada" para o pool do ODBC e a próxima chamada falha com
    # "Connection is busy with results for another command".
    while cursor.nextset():
        pass
    df = pd.DataFrame.from_records(linhas, columns=colunas)
    for coluna, tipo in tipos.items():
        if tipo is Decimal:
            df[coluna] = pd.to_numeric(df[coluna], errors="coerce").astype(float)
    return df


def consultar(procedure: str, **params) -> pd.DataFrame:
    """EXEC de uma procedure que devolve uma tabela (listagens e relatórios)."""
    sql, valores = _montar_exec(procedure, params)
    with _cursor() as cur:
        cur.execute(sql, valores)
        return _primeiro_resultado(cur)


def executar(procedure: str, **params) -> None:
    """EXEC de uma procedure sem retorno (atualizar, excluir...)."""
    sql, valores = _montar_exec(procedure, params)
    with _cursor() as cur:
        cur.execute(sql, valores)
        while cur.nextset():  # consome mensagens para pegar erros tardios
            pass


def executar_com_id(procedure: str, saida: str, **params) -> int:
    """EXEC de uma procedure com parâmetro OUTPUT (id gerado)."""
    sql, valores = _montar_exec(procedure, params)
    if not _NOME_VALIDO.match(saida):
        raise ValueError(f"Nome invalido: {saida}")
    separador = "," if params else ""
    lote = (
        "SET NOCOUNT ON; DECLARE @id INT; "
        f"{sql}{separador} @{saida} = @id OUTPUT; "
        "SELECT @id AS id;"
    )
    with _cursor() as cur:
        cur.execute(lote, valores)
        df = _primeiro_resultado(cur)
    return int(df.iloc[0, 0])


def executar_lote(lote: str, valores: list) -> pd.DataFrame:
    """Executa um lote de vários EXEC (ex.: pedido + itens numa transação)
    e devolve o primeiro resultado (o SELECT final do lote)."""
    with _cursor() as cur:
        cur.execute(lote, [parametro(v) for v in valores])
        return _primeiro_resultado(cur)

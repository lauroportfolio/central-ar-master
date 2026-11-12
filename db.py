"""Camada de acesso ao banco CentralDeAr.

Regra do projeto: a aplicação só executa STORED PROCEDURES (EXEC usp_...).
Nenhum SELECT/INSERT/UPDATE/DELETE em tabela é feito aqui.

Procedures com parâmetro OUTPUT: o pyodbc não lê OUTPUT diretamente, então
executamos um lote "DECLARE @id INT; EXEC usp_X ..., @id_x = @id OUTPUT; SELECT @id;"
e lemos o resultado do SELECT final.
"""

from __future__ import annotations

import os
import re
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pyodbc
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))


class ErroBanco(Exception):
    """Erro vindo do SQL Server (ex.: THROW das procedures) com mensagem legível."""


# ---------------------------------------------------------------------------
# Conexão
# ---------------------------------------------------------------------------

def modo_conexao() -> str:
    return os.getenv("DB_MODE", "localdb").strip().lower()


def nome_banco() -> str:
    return os.getenv("DB_NAME", "CentralDeAr").strip()


def _chaves(valor: str) -> str:
    """Protege valores da string de conexão (ex.: senha com ; ou })."""
    return "{" + valor.replace("}", "}}") + "}"


def _string_conexao() -> str:
    modo = modo_conexao()
    banco = nome_banco()

    if modo == "localdb":
        return (
            "DRIVER={ODBC Driver 18 for SQL Server};"
            r"SERVER=(localdb)\MSSQLLocalDB;"
            f"DATABASE={banco};"
            "Trusted_Connection=yes;TrustServerCertificate=yes;"
        )

    if modo == "docker":
        senha = os.getenv("DB_PASSWORD", "")
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
        return (f"Banco '{nome_banco()}' nao encontrado. Confira DB_NAME no arquivo .env "
                "e se o script sql/00_schema_reconstruido.sql foi executado.")
    if estado in ("08001", "HYT00") or "Login timeout" in texto or "network-related" in texto:
        return ("Nao foi possivel conectar ao SQL Server. Confira se o servidor esta ligado "
                f"e o DB_MODE do .env (atual: '{modo_conexao()}').")
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


def _valor(v):
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
    return sql, [_valor(v) for v in params.values()]


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


# ---------------------------------------------------------------------------
# Vendedores
# ---------------------------------------------------------------------------

def listar_vendedores() -> pd.DataFrame:
    return consultar("usp_ListarVendedores")


def cadastrar_vendedor(nome, comissao_fixa, telefone=None, email=None) -> int:
    return executar_com_id("usp_CadastrarVendedor", "id_vendedor", nome=nome,
                           comissao_fixa=comissao_fixa, telefone=telefone, email=email)


def atualizar_vendedor(id_vendedor, nome, comissao_fixa, telefone=None, email=None) -> None:
    executar("usp_AtualizarVendedor", id_vendedor=id_vendedor, nome=nome,
             comissao_fixa=comissao_fixa, telefone=telefone, email=email)


def excluir_vendedor(id_vendedor) -> None:
    executar("usp_ExcluirVendedor", id_vendedor=id_vendedor)


# ---------------------------------------------------------------------------
# Regiões
# ---------------------------------------------------------------------------

def listar_regioes() -> pd.DataFrame:
    return consultar("usp_ListarRegioes")


def cadastrar_regiao(nome, fk_vendedor, descricao=None) -> int:
    return executar_com_id("usp_CadastrarRegiao", "id_regiao", nome=nome,
                           fk_vendedor=fk_vendedor, descricao=descricao)


def atualizar_regiao(id_regiao, nome, fk_vendedor, descricao=None) -> None:
    executar("usp_AtualizarRegiao", id_regiao=id_regiao, nome=nome,
             fk_vendedor=fk_vendedor, descricao=descricao)


def excluir_regiao(id_regiao) -> None:
    executar("usp_ExcluirRegiao", id_regiao=id_regiao)


# ---------------------------------------------------------------------------
# Clientes
# ---------------------------------------------------------------------------

def listar_clientes() -> pd.DataFrame:
    return consultar("usp_ListarClientes")


def cadastrar_cliente(nome, cpf_cnpj, fk_regiao, telefone=None, email=None, endereco=None) -> int:
    return executar_com_id("usp_CadastrarCliente", "id_cliente", nome=nome, cpf_cnpj=cpf_cnpj,
                           fk_regiao=fk_regiao, telefone=telefone, email=email, endereco=endereco)


def atualizar_cliente(id_cliente, nome, cpf_cnpj, fk_regiao, telefone=None, email=None,
                      endereco=None) -> None:
    executar("usp_AtualizarCliente", id_cliente=id_cliente, nome=nome, cpf_cnpj=cpf_cnpj,
             fk_regiao=fk_regiao, telefone=telefone, email=email, endereco=endereco)


def excluir_cliente(id_cliente) -> None:
    executar("usp_ExcluirCliente", id_cliente=id_cliente)


# ---------------------------------------------------------------------------
# Produtos
# ---------------------------------------------------------------------------

def listar_produtos() -> pd.DataFrame:
    return consultar("usp_ListarProdutos")


def cadastrar_produto(descricao, preco, estoque) -> int:
    return executar_com_id("usp_CadastrarProduto", "id_produto", descricao=descricao,
                           preco=preco, estoque=estoque)


def atualizar_produto(id_produto, descricao, preco, estoque) -> None:
    executar("usp_AtualizarProduto", id_produto=id_produto, descricao=descricao,
             preco=preco, estoque=estoque)


def excluir_produto(id_produto) -> None:
    executar("usp_ExcluirProduto", id_produto=id_produto)


# ---------------------------------------------------------------------------
# Pedidos e itens
# ---------------------------------------------------------------------------

def listar_pedidos() -> pd.DataFrame:
    return consultar("usp_ListarPedidos")


def listar_itens_pedido(id_pedido) -> pd.DataFrame:
    return consultar("usp_ListarItensPedido", id_pedido=id_pedido)


def cadastrar_pedido_com_itens(fk_cliente: int, fk_vendedor: int, percentual_comissao,
                               data_pedido: datetime | None, itens: list[dict]) -> int:
    """Cria o pedido e todos os itens numa única transação (tudo ou nada).

    Só usa EXEC de procedures; se qualquer item falhar (ex.: estoque
    insuficiente na trigger), o SQL Server desfaz o pedido inteiro.
    itens: [{"fk_produto": int, "quantidade": num, "preco_unitario": num|None, "desconto": num}]
    """
    if not itens:
        raise ErroBanco("Inclua pelo menos um item no pedido.")

    linhas = [
        "SET NOCOUNT ON; SET XACT_ABORT ON;",
        "DECLARE @id INT;",
        "BEGIN TRANSACTION;",
        "EXEC usp_CadastrarPedido @fk_cliente = ?, @fk_vendedor = ?, @id_pedido = @id OUTPUT, "
        "@percentual_comissao = ?, @data_pedido = ?;",
    ]
    valores = [fk_cliente, fk_vendedor, _valor(percentual_comissao), data_pedido]
    for item in itens:
        linhas.append("EXEC usp_CadastrarItemPedido @fk_pedido = @id, @fk_produto = ?, "
                      "@quantidade = ?, @preco_unitario = ?, @desconto = ?;")
        valores += [item["fk_produto"], _valor(item["quantidade"]),
                    _valor(item.get("preco_unitario")), _valor(item.get("desconto", 0))]
    linhas += ["COMMIT TRANSACTION;", "SELECT @id AS id;"]

    with _cursor() as cur:
        cur.execute("\n".join(linhas), valores)
        df = _primeiro_resultado(cur)
    return int(df.iloc[0, 0])


def atualizar_pedido(id_pedido, fk_cliente, fk_vendedor, percentual_comissao,
                     data_pedido=None) -> None:
    executar("usp_AtualizarPedido", id_pedido=id_pedido, fk_cliente=fk_cliente,
             fk_vendedor=fk_vendedor, percentual_comissao=percentual_comissao,
             data_pedido=data_pedido)


def excluir_pedido(id_pedido) -> None:
    executar("usp_ExcluirPedido", id_pedido=id_pedido)


def cadastrar_item_pedido(fk_pedido, fk_produto, quantidade, preco_unitario=None,
                          desconto=0) -> None:
    executar("usp_CadastrarItemPedido", fk_pedido=fk_pedido, fk_produto=fk_produto,
             quantidade=quantidade, preco_unitario=preco_unitario, desconto=desconto)


def atualizar_item_pedido(fk_pedido, fk_produto, quantidade, preco_unitario=None,
                          desconto=None) -> None:
    executar("usp_AtualizarItemPedido", fk_pedido=fk_pedido, fk_produto=fk_produto,
             quantidade=quantidade, preco_unitario=preco_unitario, desconto=desconto)


def excluir_item_pedido(fk_pedido, fk_produto) -> None:
    executar("usp_ExcluirItemPedido", fk_pedido=fk_pedido, fk_produto=fk_produto)


# ---------------------------------------------------------------------------
# Relatórios
# ---------------------------------------------------------------------------

def vendas_por_regiao() -> pd.DataFrame:
    return consultar("usp_ConsultarVendasPorRegiao")


def vendas_por_cliente() -> pd.DataFrame:
    return consultar("usp_ConsultarVendasPorCliente")


def vendas_por_vendedor() -> pd.DataFrame:
    return consultar("usp_ConsultarVendasPorVendedor")


def clientes_por_regiao(id_regiao) -> pd.DataFrame:
    return consultar("usp_ConsultarClientesPorRegiao", id_regiao=id_regiao)


def vendas_por_produto() -> pd.DataFrame:
    return consultar("usp_ConsultarVendasPorProduto")


def comissao_por_vendedor(id_vendedor=None) -> pd.DataFrame:
    return consultar("usp_ConsultarComissaoPorVendedor", id_vendedor=id_vendedor)

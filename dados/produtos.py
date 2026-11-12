"""Produtos — acesso ao banco só por stored procedures."""

import pandas as pd

from dados.conexao import consultar, executar, executar_com_id


def listar() -> pd.DataFrame:
    return consultar("usp_ListarProdutos")


def cadastrar(descricao, preco, estoque) -> int:
    return executar_com_id("usp_CadastrarProduto", "id_produto", descricao=descricao,
                           preco=preco, estoque=estoque)


def atualizar(id_produto, descricao, preco, estoque) -> None:
    executar("usp_AtualizarProduto", id_produto=id_produto, descricao=descricao,
             preco=preco, estoque=estoque)


def excluir(id_produto) -> None:
    executar("usp_ExcluirProduto", id_produto=id_produto)

"""Vendedores — acesso ao banco só por stored procedures."""

import pandas as pd

from dados.conexao import consultar, executar, executar_com_id


def listar() -> pd.DataFrame:
    return consultar("usp_ListarVendedores")


def cadastrar(nome, comissao_fixa, telefone=None, email=None) -> int:
    return executar_com_id("usp_CadastrarVendedor", "id_vendedor", nome=nome,
                           comissao_fixa=comissao_fixa, telefone=telefone, email=email)


def atualizar(id_vendedor, nome, comissao_fixa, telefone=None, email=None) -> None:
    executar("usp_AtualizarVendedor", id_vendedor=id_vendedor, nome=nome,
             comissao_fixa=comissao_fixa, telefone=telefone, email=email)


def excluir(id_vendedor) -> None:
    executar("usp_ExcluirVendedor", id_vendedor=id_vendedor)

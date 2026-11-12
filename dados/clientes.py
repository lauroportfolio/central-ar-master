"""Clientes — acesso ao banco só por stored procedures."""

import pandas as pd

from dados.conexao import consultar, executar, executar_com_id


def listar() -> pd.DataFrame:
    return consultar("usp_ListarClientes")


def cadastrar(nome, cpf_cnpj, fk_regiao, telefone=None, email=None, endereco=None) -> int:
    return executar_com_id("usp_CadastrarCliente", "id_cliente", nome=nome, cpf_cnpj=cpf_cnpj,
                           fk_regiao=fk_regiao, telefone=telefone, email=email, endereco=endereco)


def atualizar(id_cliente, nome, cpf_cnpj, fk_regiao, telefone=None, email=None,
              endereco=None) -> None:
    executar("usp_AtualizarCliente", id_cliente=id_cliente, nome=nome, cpf_cnpj=cpf_cnpj,
             fk_regiao=fk_regiao, telefone=telefone, email=email, endereco=endereco)


def excluir(id_cliente) -> None:
    executar("usp_ExcluirCliente", id_cliente=id_cliente)

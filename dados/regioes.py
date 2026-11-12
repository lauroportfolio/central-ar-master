"""Regiões — acesso ao banco só por stored procedures."""

import pandas as pd

from dados.conexao import consultar, executar, executar_com_id


def listar() -> pd.DataFrame:
    return consultar("usp_ListarRegioes")


def cadastrar(nome, fk_vendedor, descricao=None) -> int:
    return executar_com_id("usp_CadastrarRegiao", "id_regiao", nome=nome,
                           fk_vendedor=fk_vendedor, descricao=descricao)


def atualizar(id_regiao, nome, fk_vendedor, descricao=None) -> None:
    executar("usp_AtualizarRegiao", id_regiao=id_regiao, nome=nome,
             fk_vendedor=fk_vendedor, descricao=descricao)


def excluir(id_regiao) -> None:
    executar("usp_ExcluirRegiao", id_regiao=id_regiao)

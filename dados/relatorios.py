"""Relatórios — cada um é uma stored procedure de consulta."""

import pandas as pd

from dados.conexao import consultar


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

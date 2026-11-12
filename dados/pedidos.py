"""Pedidos e itens de pedido — acesso ao banco só por stored procedures.

O estoque é ajustado no banco pela trigger trg_ITEM_PEDIDO_Estoque.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from dados.conexao import consultar, executar, executar_lote
from util.erros import ErroBanco


def listar() -> pd.DataFrame:
    return consultar("usp_ListarPedidos")


def listar_itens(id_pedido) -> pd.DataFrame:
    return consultar("usp_ListarItensPedido", id_pedido=id_pedido)


def cadastrar_com_itens(fk_cliente: int, fk_vendedor: int, percentual_comissao,
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
    valores = [fk_cliente, fk_vendedor, percentual_comissao, data_pedido]
    for item in itens:
        linhas.append("EXEC usp_CadastrarItemPedido @fk_pedido = @id, @fk_produto = ?, "
                      "@quantidade = ?, @preco_unitario = ?, @desconto = ?;")
        valores += [item["fk_produto"], item["quantidade"],
                    item.get("preco_unitario"), item.get("desconto", 0)]
    linhas += ["COMMIT TRANSACTION;", "SELECT @id AS id;"]

    df = executar_lote("\n".join(linhas), valores)
    return int(df.iloc[0, 0])


def atualizar(id_pedido, fk_cliente, fk_vendedor, percentual_comissao, data_pedido=None) -> None:
    executar("usp_AtualizarPedido", id_pedido=id_pedido, fk_cliente=fk_cliente,
             fk_vendedor=fk_vendedor, percentual_comissao=percentual_comissao,
             data_pedido=data_pedido)


def excluir(id_pedido) -> None:
    executar("usp_ExcluirPedido", id_pedido=id_pedido)


def cadastrar_item(fk_pedido, fk_produto, quantidade, preco_unitario=None, desconto=0) -> None:
    executar("usp_CadastrarItemPedido", fk_pedido=fk_pedido, fk_produto=fk_produto,
             quantidade=quantidade, preco_unitario=preco_unitario, desconto=desconto)


def atualizar_item(fk_pedido, fk_produto, quantidade, preco_unitario=None, desconto=None) -> None:
    executar("usp_AtualizarItemPedido", fk_pedido=fk_pedido, fk_produto=fk_produto,
             quantidade=quantidade, preco_unitario=preco_unitario, desconto=desconto)


def excluir_item(fk_pedido, fk_produto) -> None:
    executar("usp_ExcluirItemPedido", fk_pedido=fk_pedido, fk_produto=fk_produto)

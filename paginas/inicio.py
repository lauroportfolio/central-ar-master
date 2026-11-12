"""Tela Início: indicadores, vendas por região e últimos pedidos."""

from html import escape

import streamlit as st

from componentes.acoes import carregar
from componentes.grafico import grafico_barras
from componentes.layout import painel, titulo_html
from dados import clientes as dados_clientes
from dados import pedidos as dados_pedidos
from dados import produtos as dados_produtos
from dados import relatorios as dados_relatorios
from dados import vendedores as dados_vendedores
from util.formatacao import brl, data_hora


def render() -> None:
    pedidos = carregar(dados_pedidos.listar)
    vendedores = carregar(dados_vendedores.listar)
    regioes = carregar(dados_relatorios.vendas_por_regiao)
    clientes = carregar(dados_clientes.listar)
    produtos = carregar(dados_produtos.listar)

    total = pedidos["total_pedido"].sum() if not pedidos.empty else 0
    comissoes = pedidos["valor_comissao"].sum() if not pedidos.empty else 0
    ticket = total / len(pedidos) if len(pedidos) else 0

    principal, lateral = st.columns([7, 3])

    with principal, painel("inicio", "Visão geral"):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total vendido", brl(total), border=True)
        c2.metric("Pedidos", len(pedidos), border=True)
        c3.metric("Ticket médio", brl(ticket), border=True)
        c4.metric("Comissões", brl(comissoes), border=True)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Vendedores", len(vendedores), border=True)
        c2.metric("Regiões", len(regioes), border=True)
        c3.metric("Clientes", len(clientes), border=True)
        c4.metric("Produtos", len(produtos), border=True)
        st.html(titulo_html("Vendas por região"))
        if regioes.empty or regioes["total_vendido"].sum() == 0:
            st.info("Ainda não há vendas.")
        else:
            grafico_barras(regioes, "regiao", "total_vendido", "Região", preencher=True)

    with lateral, painel("ultimos", "Últimos pedidos"):
        if pedidos.empty:
            st.info("Nenhum pedido cadastrado.")
        else:
            itens = "".join(
                f'<div class="item-pedido">'
                f'<div class="cliente">Nº {r.id_pedido} · {escape(str(r.cliente))}</div>'
                f'<div class="total">{brl(r.total_pedido)}</div>'
                f'<div class="detalhe">{data_hora(r.data_pedido)} · {escape(str(r.vendedor))}</div>'
                f'</div>'
                for r in pedidos.itertuples())
            st.html(f'<div class="lista-pedidos">{itens}</div>')

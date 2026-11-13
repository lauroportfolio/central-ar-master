"""Tela Início: indicadores, vendas por região e últimos pedidos."""

import streamlit as st

from componentes.acoes import carregar
from componentes.dicas import ajuda, com_dica, texto_cortado
from componentes.grafico import grafico_barras
from componentes.layout import painel, titulo_html
from dados import clientes as dados_clientes
from dados import pedidos as dados_pedidos
from dados import produtos as dados_produtos
from dados import relatorios as dados_relatorios
from dados import vendedores as dados_vendedores
from util.formatacao import brl, data_hora, pct
from util.i18n import t

KPI = "inicio.kpi"


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

    with principal, painel("inicio", t("inicio.visao_geral")):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(t(f"{KPI}.total_vendido"), brl(total), border=True, help=ajuda("tooltips.kpi.total_vendido"))
        c2.metric(t(f"{KPI}.pedidos"), len(pedidos), border=True, help=ajuda("tooltips.kpi.pedidos"))
        c3.metric(t(f"{KPI}.ticket_medio"), brl(ticket), border=True, help=ajuda("tooltips.kpi.ticket_medio"))
        c4.metric(t(f"{KPI}.comissoes"), brl(comissoes), border=True, help=ajuda("tooltips.kpi.comissoes"))
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(t(f"{KPI}.vendedores"), len(vendedores), border=True, help=ajuda("tooltips.kpi.vendedores"))
        c2.metric(t(f"{KPI}.regioes"), len(regioes), border=True, help=ajuda("tooltips.kpi.regioes"))
        c3.metric(t(f"{KPI}.clientes"), len(clientes), border=True, help=ajuda("tooltips.kpi.clientes"))
        c4.metric(t(f"{KPI}.produtos"), len(produtos), border=True, help=ajuda("tooltips.kpi.produtos"))
        st.html(titulo_html(t("inicio.vendas_por_regiao")))
        if regioes.empty or regioes["total_vendido"].sum() == 0:
            st.info(t("inicio.sem_vendas"))
        else:
            grafico_barras(regioes, "regiao", "total_vendido", t("comum.regiao"), preencher=True)

    with lateral, painel("ultimos", t("inicio.ultimos_pedidos")):
        if pedidos.empty:
            st.info(t("inicio.sem_pedidos"))
        else:
            itens = "".join(
                com_dica(
                    f'<div class="item-pedido">'
                    f'<div class="cliente">{texto_cortado(t("inicio.item_titulo", id=r.id_pedido, cliente=r.cliente))}</div>'
                    f'<div class="total">{brl(r.total_pedido)}</div>'
                    f'<div class="detalhe">{texto_cortado(t("inicio.item_detalhe", data=data_hora(r.data_pedido), vendedor=r.vendedor))}</div>'
                    f'</div>',
                    "tooltips.ultimo_pedido", bloco=True, vendedor=r.vendedor,
                    comissao=brl(r.valor_comissao), percentual=pct(r.percentual_comissao))
                for r in pedidos.itertuples())
            st.html(f'<div class="lista-pedidos">{itens}</div>')

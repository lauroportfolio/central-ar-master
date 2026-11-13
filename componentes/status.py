"""Faixa de status abaixo da navbar: bolinha colorida + número + rótulo.

Recebe os dados prontos (quem busca no banco é o app.py).
"""

from html import escape

import pandas as pd
import streamlit as st

from componentes.dicas import com_dica
from util.formatacao import brl_curto
from util.i18n import t, t_plural

ESTOQUE_BAIXO = 10  # produtos com menos que isso aparecem no alerta vermelho


def faixa_status(pedidos: pd.DataFrame, vendedores: pd.DataFrame, produtos: pd.DataFrame,
                 banco: str, modo: str) -> None:
    total = pedidos["total_pedido"].sum() if not pedidos.empty else 0
    baixo = int((produtos["estoque"] < ESTOQUE_BAIXO).sum()) if not produtos.empty else 0
    itens = [
        ("verde", f"{len(pedidos)}", t_plural("status.pedidos", len(pedidos)), "tooltips.status.pedidos"),
        ("azul", brl_curto(total), t("status.vendidos"), "tooltips.status.vendidos"),
        ("amarelo", f"{len(vendedores)}", t_plural("status.vendedores", len(vendedores)), "tooltips.status.vendedores"),
    ]
    if baixo:
        itens.append(("vermelho", f"{baixo}", t_plural("status.estoque_baixo", baixo), "tooltips.status.estoque_baixo"))
    else:
        itens.append(("verde", t("status.estoque"), t("status.estoque_ok"), "tooltips.status.estoque_ok"))
    html = "".join(
        com_dica(f'<span class="item"><span class="ponto {cor}"></span><b>{escape(num)}</b> {escape(rot)}</span>',
                 dica, alinhamento="inicio", limite=ESTOQUE_BAIXO)
        for cor, num, rot, dica in itens)
    html += com_dica(f'<span class="banco">{t("status.banco", banco=f"<b>{escape(banco)}</b>", modo=escape(modo))}</span>',
                     "tooltips.status.banco", alinhamento="fim")
    st.html(f'<div class="faixa-status">{html}</div>')


def faixa_sem_conexao() -> None:
    st.html('<div class="faixa-status"><span class="item"><span class="ponto vermelho"></span>'
            f'<b>{escape(t("status.sem_conexao"))}</b></span></div>')

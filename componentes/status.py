"""Faixa de status abaixo da navbar: bolinha colorida + número + rótulo.

Recebe os dados prontos (quem busca no banco é o app.py).
"""

from html import escape

import pandas as pd
import streamlit as st

from util.formatacao import brl_curto

ESTOQUE_BAIXO = 10  # produtos com menos que isso aparecem no alerta vermelho


def faixa_status(pedidos: pd.DataFrame, vendedores: pd.DataFrame, produtos: pd.DataFrame,
                 banco: str, modo: str) -> None:
    total = pedidos["total_pedido"].sum() if not pedidos.empty else 0
    baixo = int((produtos["estoque"] < ESTOQUE_BAIXO).sum()) if not produtos.empty else 0
    itens = [
        ("verde", f"{len(pedidos)}", "pedidos" if len(pedidos) != 1 else "pedido"),
        ("azul", brl_curto(total), "vendidos"),
        ("amarelo", f"{len(vendedores)}", "vendedores" if len(vendedores) != 1 else "vendedor"),
    ]
    if baixo:
        itens.append(("vermelho", f"{baixo}",
                      "produto com estoque baixo" if baixo == 1 else "produtos com estoque baixo"))
    else:
        itens.append(("verde", "Estoque", "ok"))
    html = "".join(f'<span class="item"><span class="ponto {cor}"></span><b>{escape(num)}</b> {escape(rot)}</span>'
                   for cor, num, rot in itens)
    html += (f'<span class="banco">Banco <b>{escape(banco)}</b> · '
             f'modo {escape(modo)}</span>')
    st.html(f'<div class="faixa-status">{html}</div>')


def faixa_sem_conexao() -> None:
    st.html('<div class="faixa-status"><span class="item"><span class="ponto vermelho"></span>'
            '<b>Sem conexão com o banco</b></span></div>')

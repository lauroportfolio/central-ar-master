"""Painéis com scroll interno e títulos (o CSS do layout está em ui/estilo.css)."""

from __future__ import annotations

from html import escape

import streamlit as st


def titulo_html(titulo: str, subtitulo: str | None = None) -> str:
    html = f'<div class="painel-titulo">{escape(titulo)}</div>'
    if subtitulo:
        html += f'<div class="painel-subtitulo">{escape(subtitulo)}</div>'
    return html


def painel(chave: str, titulo: str | None = None, subtitulo: str | None = None,
           borda: bool = True):
    """Cartão com scroll interno que ocupa a altura restante da janela.
    O key "painel_..." é o que o CSS usa para esticar o painel até o fim da tela."""
    caixa = st.container(key=f"painel_{chave}", border=borda, height="stretch")
    if titulo:
        caixa.html(titulo_html(titulo, subtitulo))
    return caixa


def lado_a_lado(chave: str, proporcao=(1, 1)):
    """Gráfico e tabela lado a lado, cada um com scroll próprio dentro da aba."""
    c1, c2 = st.columns(list(proporcao), gap="medium")
    with c1:
        esquerda = st.container(key=f"painel_{chave}_grafico", height="stretch")
    with c2:
        direita = st.container(key=f"painel_{chave}_tabela", height="stretch")
    return esquerda, direita

"""Gráfico de barras horizontais (Altair)."""

import altair as alt
import pandas as pd
import streamlit as st

from util.formatacao import brl

COR_BARRA = "#1E6FD9"


def grafico_barras(df: pd.DataFrame, categoria: str, valor: str, titulo_categoria: str,
                   titulo_valor: str = "Total vendido (R$)", preencher: bool = False) -> None:
    """Barras horizontais (uma série só), ordenadas do maior para o menor, com tooltip em R$.

    preencher=False: altura proporcional ao número de barras (o painel rola se precisar).
    preencher=True : ocupa a altura que sobra no painel; a espessura da barra é limitada
                     (no máximo 28 px e 60% da faixa de cada categoria), sem sobreposição.
    """
    dados = df[[categoria, valor]].copy()
    dados = dados[dados[valor] > 0]
    if dados.empty:
        st.caption("Sem vendas para mostrar no gráfico.")
        return
    dados["valor_formatado"] = dados[valor].map(brl)
    # Altura proporcional ao número de barras (32 px por categoria + eixo).
    # A altura é passada também ao st.altair_chart, senão o Streamlit encolhe o gráfico.
    altura = 32 * len(dados) + 56
    barra = {"size": alt.ExprRef("min(28, bandwidth('y') * 0.6)")} if preencher else {}
    grafico = (
        alt.Chart(dados, background="transparent")
        .mark_bar(color=COR_BARRA, cornerRadiusEnd=4, **barra)
        .encode(
            y=alt.Y(f"{categoria}:N", sort="-x", title=None,
                    scale=alt.Scale(paddingInner=0.3, paddingOuter=0.15),
                    axis=alt.Axis(labelLimit=220, labelOverlap=False)),
            x=alt.X(f"{valor}:Q", title=titulo_valor,
                    axis=alt.Axis(format="~s", grid=True, tickCount=6)),
            tooltip=[alt.Tooltip(f"{categoria}:N", title=titulo_categoria),
                     alt.Tooltip("valor_formatado:N", title=titulo_valor.replace(" (R$)", ""))],
        )
        .properties(height="container" if preencher else altura - 56)
        .configure_axis(gridOpacity=0.35, domain=False, tickColor="transparent")
        .configure_view(strokeWidth=0)
    )
    st.altair_chart(grafico, width="stretch", height="stretch" if preencher else altura)

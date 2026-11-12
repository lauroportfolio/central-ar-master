"""Tabela formatada (R$, %, datas), busca e seleção de linha."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from util.formatacao import brl, data_curta, data_hora, pct, qtd, texto


def tabela(df: pd.DataFrame, colunas: dict[str, str], moeda=(), percentual=(),
           quantidade=(), datas=(), datas_curtas=(), altura="stretch", chave: str | None = None,
           larguras: dict[str, int] | None = None):
    """st.dataframe com cabeçalhos em português e valores formatados (R$, %, datas).
    Com `chave`, permite selecionar uma linha e devolve a posição dela (ou None).
    `larguras` fixa a largura (px) de colunas específicas, ex.: {"produto": 180}."""
    if df.empty:
        st.info("Nenhum registro encontrado.")
        return None
    visivel = df[list(colunas)].rename(columns=colunas)
    formatos = {}
    for grupo, funcao in ((moeda, brl), (percentual, pct), (quantidade, qtd), (datas, data_hora),
                          (datas_curtas, data_curta)):
        for coluna in grupo:
            formatos[colunas[coluna]] = funcao
    textos = [colunas[c] for c in colunas
              if c not in (*moeda, *percentual, *quantidade, *datas, *datas_curtas)
              and visivel[colunas[c]].dtype != "int64"]
    for coluna in textos:
        formatos.setdefault(coluna, texto)
    # Largura mínima para valores formatados não serem cortados ("R$ 2.84...")
    config_colunas = {}
    for grupo, px in ((moeda, 130), (datas, 135), (datas_curtas, 95), (percentual, 105),
                      (quantidade, 100)):
        for coluna in grupo:
            config_colunas[colunas[coluna]] = st.column_config.Column(width=px)
    for coluna, px in (larguras or {}).items():
        config_colunas[colunas[coluna]] = st.column_config.Column(width=px)
    selecao = {}
    if chave:
        selecao = {"on_select": "rerun", "selection_mode": "single-row", "key": chave}
    evento = st.dataframe(visivel.style.format(formatos), hide_index=True, width="stretch",
                          height=altura, column_config=config_colunas, **selecao)
    if chave and evento.selection.rows:
        return evento.selection.rows[0]
    return None


def filtrar(df: pd.DataFrame, termo: str | None) -> pd.DataFrame:
    """Busca simples: mantém as linhas em que alguma coluna contém o termo."""
    termo = (termo or "").strip().casefold()
    if not termo or df.empty:
        return df
    achou = df.astype(str).apply(lambda col: col.str.casefold().str.contains(termo, regex=False))
    return df[achou.any(axis=1)]


def versao_selecao(chave: str) -> int:
    return st.session_state.setdefault(f"_versao_{chave}", 0)


def limpar_selecao(chave: str) -> None:
    """Desmarca a linha selecionada na tabela (troca o key do dataframe)."""
    st.session_state[f"_versao_{chave}"] = versao_selecao(chave) + 1

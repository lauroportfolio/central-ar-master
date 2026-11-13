"""Peças comuns às telas de cadastro: lista com busca, cabeçalho de edição e exclusão."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from componentes.acoes import executar
from componentes.layout import painel, titulo_html
from componentes.tabela import filtrar, limpar_selecao, tabela_selecionavel
from util.i18n import t


def lista_com_busca(chave: str, titulo: str, df: pd.DataFrame, colunas: dict[str, str],
                    coluna_id: str, **formatos):
    """Painel esquerdo dos cadastros. Devolve a linha selecionada (Series) ou None.
    A seleção é guardada pelo ID (coluna_id), não pela posição na tabela."""
    with painel(f"lista_{chave}"):
        c1, c2 = st.columns([1, 1], vertical_alignment="center")
        # .marca-cadastros: faz o CSS sublinhar "Cadastros" na navbar nestas telas
        c1.html(titulo_html(titulo, t("comum.registros", n=len(df)))
                + '<span class="marca-cadastros"></span>')
        termo = c2.text_input(t("comum.buscar"), placeholder=t("comum.buscar_placeholder"),
                              label_visibility="collapsed", key=f"busca_{chave}", icon=":material/search:")
        visivel = filtrar(df, termo).reset_index(drop=True)
        id_sel = tabela_selecionavel(chave, visivel, colunas, coluna_id, **formatos)
    return None if id_sel is None else visivel[visivel[coluna_id] == id_sel].iloc[0]


def cabecalho_edicao(chave: str, titulo: str, subtitulo: str | None = None, ajuda: str | None = None) -> None:
    """Título do formulário de edição + botão "Novo" (desmarca a linha)."""
    c1, c2 = st.columns([3, 1], vertical_alignment="center")
    c1.html(titulo_html(titulo, subtitulo))
    c2.button(t("comum.novo"), icon=":material/add:", key=f"novo_{chave}", width="stretch",
              on_click=limpar_selecao, args=(chave,), help=ajuda)


def form_excluir(area: str, id_, funcao, sucesso: str, aviso: str | None = None,
                 ao_sucesso=None, ajuda: str | None = None) -> None:
    """Formulário de exclusão com caixa de confirmação.
    `area`: chave do idioma com os textos da entidade (ex.: "cadastros.regioes"),
    que tem excluir_titulo, excluir_confirmar e excluir_botao."""
    with st.form(f"{area}_excluir_{id_}"):
        st.markdown(f"**{t(f'{area}.excluir_titulo')}**")
        if aviso:
            st.caption(aviso)
        confirma = st.checkbox(t(f"{area}.excluir_confirmar"))
        if st.form_submit_button(t(f"{area}.excluir_botao"), icon="🗑️", help=ajuda):
            if not confirma:
                st.warning(t("comum.marque_confirmacao"))
            else:
                executar(funcao, int(id_), sucesso=sucesso, ao_sucesso=ao_sucesso)

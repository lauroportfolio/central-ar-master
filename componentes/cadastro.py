"""Peças comuns às telas de cadastro: lista com busca, cabeçalho de edição e exclusão."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from componentes.acoes import executar
from componentes.layout import painel, titulo_html
from componentes.tabela import filtrar, limpar_selecao, tabela, versao_selecao


def lista_com_busca(chave: str, titulo: str, df: pd.DataFrame, colunas: dict[str, str], **formatos):
    """Painel esquerdo dos cadastros. Devolve a linha selecionada (Series) ou None."""
    with painel(f"lista_{chave}"):
        c1, c2 = st.columns([1, 1], vertical_alignment="center")
        # .marca-cadastros: faz o CSS sublinhar "Cadastros" na navbar nestas telas
        c1.html(titulo_html(titulo, f"{len(df)} registro(s) · clique numa linha para editar")
                + '<span class="marca-cadastros"></span>')
        termo = c2.text_input("Buscar", placeholder="Buscar...", label_visibility="collapsed",
                              key=f"busca_{chave}", icon=":material/search:")
        visivel = filtrar(df, termo).reset_index(drop=True)
        posicao = tabela(visivel, colunas, chave=f"tabela_{chave}_{versao_selecao(chave)}_{termo}",
                         **formatos)
    return None if posicao is None or posicao >= len(visivel) else visivel.iloc[posicao]


def cabecalho_edicao(chave: str, titulo: str, subtitulo: str | None = None) -> None:
    """Título do formulário de edição + botão "Novo" (desmarca a linha)."""
    c1, c2 = st.columns([3, 1], vertical_alignment="center")
    c1.html(titulo_html(titulo, subtitulo))
    c2.button("Novo", icon=":material/add:", key=f"novo_{chave}", width="stretch",
              on_click=limpar_selecao, args=(chave,), help="Desmarcar a linha e cadastrar um novo")


def form_excluir(entidade: str, id_, funcao, sucesso: str, aviso: str | None = None,
                 ao_sucesso=None) -> None:
    """Formulário de exclusão com caixa de confirmação."""
    with st.form(f"{entidade}_excluir_{id_}"):
        st.markdown(f"**Excluir {entidade}**")
        if aviso:
            st.caption(aviso)
        confirma = st.checkbox(f"Confirmo que quero excluir este {entidade}")
        if st.form_submit_button(f"Excluir {entidade}", icon="🗑️"):
            if not confirma:
                st.warning("Marque a confirmação para excluir.")
            else:
                executar(funcao, int(id_), sucesso=sucesso, ao_sucesso=ao_sucesso)

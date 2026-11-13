"""Idioma da interface: escolha no canto da navbar, guardada na sessão e na URL (?lang=en).

O menu ⋮ do Streamlit só aceita os itens fixos "Get help", "Report a bug" e "About"
(st.set_page_config(menu_items=...)), sem ações próprias. Por isso o seletor é um
st.popover que o CSS (ui/estilo.css) posiciona na navbar, ao lado do ⋮.
"""

from __future__ import annotations

import streamlit as st

from util.i18n import CHAVE_SESSAO, IDIOMAS, PADRAO, idioma_atual, t

_PARAMETRO = "lang"
_CHAVE_WIDGET = "_escolha_idioma"


def inicializar_idioma() -> None:
    """Chamar no começo de cada execução, antes de qualquer t().
    Sessão nova (inclusive depois do F5): o idioma vem do ?lang= da URL; padrão pt.
    Depois, a URL acompanha a sessão (some quando o idioma é o padrão)."""
    if CHAVE_SESSAO not in st.session_state:
        da_url = st.query_params.get(_PARAMETRO)
        st.session_state[CHAVE_SESSAO] = da_url if da_url in IDIOMAS else PADRAO
    idioma = idioma_atual()
    if idioma == PADRAO:
        if _PARAMETRO in st.query_params:
            del st.query_params[_PARAMETRO]
    elif st.query_params.get(_PARAMETRO) != idioma:
        st.query_params[_PARAMETRO] = idioma


def _trocar_idioma() -> None:
    st.session_state[CHAVE_SESSAO] = st.session_state[_CHAVE_WIDGET]


def seletor_idioma(ajuda: str | None = None) -> None:
    """Botão compacto ("PT"/"EN") com a lista de idiomas, no canto direito da navbar."""
    with st.container(key="seletor_idioma"):
        with st.popover(t("idioma.sigla"), icon=":material/translate:", help=ajuda):
            st.radio(t("idioma.rotulo"), IDIOMAS, index=IDIOMAS.index(idioma_atual()),
                     format_func=lambda codigo: t(f"idioma.{codigo}"),
                     key=_CHAVE_WIDGET, on_change=_trocar_idioma)

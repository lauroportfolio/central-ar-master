"""Tradução da interface (pt-BR / en) sem biblioteca extra.

- Os textos ficam em locale/<idioma>.json, com chaves aninhadas por área
  (nav, status, inicio, pedidos, relatorios, cadastros.vendedores, comum, erros, tooltips).
- t("pedidos.detalhe.titulo", id=15) busca a chave no idioma atual e interpola {id}.
- Chave que falta no idioma: usa o português e avisa no log (uma vez por chave).
- O idioma atual fica em st.session_state["idioma"] (padrão: pt).
"""

from __future__ import annotations

import json
import logging
import re
from functools import cache
from pathlib import Path

IDIOMAS = ("pt", "en")
PADRAO = "pt"
CHAVE_SESSAO = "idioma"

_PASTA = Path(__file__).resolve().parent.parent / "locale"
_log = logging.getLogger("central_ar.i18n")
_avisadas: set[tuple[str, str]] = set()


@cache
def _textos(idioma: str) -> dict:
    with open(_PASTA / f"{idioma}.json", encoding="utf-8") as arquivo:
        return json.load(arquivo)


def _buscar(arvore: dict, chave: str):
    no = arvore
    for parte in chave.split("."):
        if not isinstance(no, dict) or parte not in no:
            return None
        no = no[parte]
    return no


def idioma_atual() -> str:
    try:
        import streamlit as st
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        if get_script_run_ctx(suppress_warning=True) is None:   # fora do Streamlit (scripts, testes)
            return PADRAO
        idioma = st.session_state.get(CHAVE_SESSAO, PADRAO)
    except Exception:
        idioma = PADRAO
    return idioma if idioma in IDIOMAS else PADRAO


class _Faltando(dict):
    """Deixa {marcador} sem valor como está, em vez de dar erro."""
    def __missing__(self, chave):
        return "{" + chave + "}"


def existe(chave: str) -> bool:
    return isinstance(_buscar(_textos(idioma_atual()), chave), str) or \
        isinstance(_buscar(_textos(PADRAO), chave), str)


def t(chave: str, **parametros) -> str:
    """Texto da chave no idioma atual, com {marcadores} preenchidos."""
    idioma = idioma_atual()
    valor = _buscar(_textos(idioma), chave)
    if not isinstance(valor, str):
        if (idioma, chave) not in _avisadas:
            _avisadas.add((idioma, chave))
            _log.warning("i18n: chave '%s' não existe em %s.json", chave, idioma)
        valor = _buscar(_textos(PADRAO), chave) if idioma != PADRAO else None
        if not isinstance(valor, str):
            return chave
    return valor.format_map(_Faltando(parametros)) if parametros else valor


def t_plural(chave: str, n: int, **parametros) -> str:
    """Escolhe <chave>.um (n == 1) ou <chave>.outros."""
    return t(f"{chave}.{'um' if n == 1 else 'outros'}", n=n, **parametros)


# ------------------------------------------------------------------ erros do banco
# Os THROW das procedures (50001...) viram chaves erros.<código>. Mensagens com valores
# (quantidades, produto...) têm os valores recuperados do texto original do banco.
_VALORES_DO_ERRO = {
    50022: r'produto "(?P<produto>.*)" \(codigo (?P<codigo>\d+)\)\. Disponivel: (?P<disponivel>[\d.,]+); '
           r'necessario: (?P<necessario>[\d.,]+)',
    50023: r"responsavel por (?P<qtd>\d+)",
    50024: r"possui (?P<qtd>\d+)",
    50025: r"possui (?P<qtd>\d+)",
    50026: r"possui (?P<qtd>\d+)",
    50027: r"aparece em (?P<qtd>\d+)",
}


def traduzir_erro(mensagem: str, codigo: int | None = None, chave: str | None = None,
                  parametros: dict | None = None) -> str:
    """Mensagem de erro do banco no idioma atual.
    Código conhecido -> erros.<código>; chave especial -> t(chave); senão, o texto original."""
    parametros = dict(parametros or {})
    if codigo is not None and existe(f"erros.{codigo}"):
        padrao = _VALORES_DO_ERRO.get(codigo)
        if padrao:
            achou = re.search(padrao, mensagem)
            if not achou:
                return mensagem
            parametros.update(achou.groupdict())
        return t(f"erros.{codigo}", **parametros)
    if chave and existe(chave):
        return t(chave, **parametros)
    return mensagem

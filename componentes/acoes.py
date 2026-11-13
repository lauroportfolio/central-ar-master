"""Ler e gravar com tratamento de erro do banco, e avisos de sucesso.

As funções recebem a função de dados como parâmetro (ex.: dados_vendedores.listar),
então este módulo não depende da camada de dados.
"""

import streamlit as st

from util.erros import ErroBanco
from util.i18n import t, traduzir_erro

_CHAVE_AVISO = "_aviso"


def mensagem_de_erro(erro: ErroBanco) -> str:
    """Mensagem do banco no idioma da tela (pelo número do THROW ou pela chave do erro)."""
    return traduzir_erro(erro.mensagem, erro.codigo, erro.chave, erro.parametros)


def carregar(funcao, *args):
    """Lê dados do banco; se der erro, mostra a mensagem e para a página."""
    try:
        return funcao(*args)
    except ErroBanco as erro:
        st.error(t("comum.erro_banco", erro=mensagem_de_erro(erro)), icon="🚫")
        st.stop()


def executar(funcao, *args, sucesso: str, ao_sucesso=None, **kwargs) -> None:
    """Grava no banco. Erro (THROW do SQL Server) -> st.error com a mensagem do banco traduzida,
    dentro do painel do formulário (o painel rola; a página não).
    `sucesso` já vem traduzido; pode ter {id} para o código gerado."""
    try:
        resultado = funcao(*args, **kwargs)
    except ErroBanco as erro:
        st.error(mensagem_de_erro(erro), icon="🚫")
        return
    if ao_sucesso:
        ao_sucesso()
    avisar(sucesso.replace("{id}", str(resultado)))
    st.rerun()


def avisar(texto: str) -> None:
    """Guarda um aviso de sucesso para mostrar depois do rerun."""
    st.session_state[_CHAVE_AVISO] = texto


def mostrar_aviso() -> None:
    """Mensagem de sucesso como toast (não ocupa espaço no layout)."""
    aviso = st.session_state.pop(_CHAVE_AVISO, None)
    if aviso:
        st.toast(aviso, icon="✅", duration="long")

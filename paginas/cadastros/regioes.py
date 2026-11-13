"""Cadastro de regiões (região fechada: um único vendedor por região)."""

import pandas as pd
import streamlit as st

from componentes.acoes import carregar, executar
from componentes.dicas import ajuda
from componentes.cadastro import cabecalho_edicao, form_excluir, lista_com_busca
from componentes.layout import painel, titulo_html
from componentes.tabela import limpar_selecao
from dados import regioes as dados_regioes
from dados import vendedores as dados_vendedores
from util.formatacao import opcional, texto
from util.i18n import t

AREA = "cadastros.regioes"


def _rotulo_por_id(df: pd.DataFrame, coluna_id: str, coluna_nome: str):
    nomes = dict(zip(df[coluna_id], df[coluna_nome]))
    return lambda i: f"{i} — {nomes.get(i, '')}"


def render() -> None:
    df = carregar(dados_regioes.listar)
    vendedores = carregar(dados_vendedores.listar)
    esquerda, direita = st.columns([3, 2])
    with esquerda:
        sel = lista_com_busca("regioes", t(f"{AREA}.titulo"), df,
                              {"id_regiao": t("comum.codigo"), "nome": t("comum.regiao"),
                               "descricao": t("comum.descricao"), "vendedor": t(f"{AREA}.col_vendedor"),
                               "qtd_clientes": t("comum.clientes")},
                              coluna_id="id_regiao")

    with direita, painel("form_regioes"):
        if vendedores.empty:
            st.info(t(f"{AREA}.sem_vendedores"))
            return
        nome_vendedor = _rotulo_por_id(vendedores, "id_vendedor", "nome")
        ids_vendedores = list(vendedores["id_vendedor"])

        if sel is None:
            st.html(titulo_html(t(f"{AREA}.novo"), t(f"{AREA}.novo_subtitulo")))
            with st.form("regiao_incluir", clear_on_submit=True):
                nome = st.text_input(t(f"{AREA}.campo_nome"))
                vendedor = st.selectbox(t(f"{AREA}.campo_vendedor"), ids_vendedores, format_func=nome_vendedor,
                                        key="regiao_incluir_vendedor")
                descricao = st.text_area(t(f"{AREA}.campo_descricao_novo"), height=80)
                if st.form_submit_button(t(f"{AREA}.botao_cadastrar"), type="primary"):
                    executar(dados_regioes.cadastrar, nome.strip(), int(vendedor), opcional(descricao),
                             sucesso=t(f"{AREA}.cadastrado"))
            return

        id_ = int(sel["id_regiao"])
        cabecalho_edicao("regioes", t(f"{AREA}.editar", id=id_), texto(sel["nome"]), ajuda=ajuda("tooltips.novo"))
        with st.form(f"regiao_editar_{id_}"):
            nome = st.text_input(t(f"{AREA}.campo_nome"), texto(sel["nome"]))
            vendedor = st.selectbox(t(f"{AREA}.campo_vendedor"), ids_vendedores, format_func=nome_vendedor,
                                    index=ids_vendedores.index(sel["id_vendedor"]), key=f"regiao_editar_vendedor_{id_}")
            descricao = st.text_area(t(f"{AREA}.campo_descricao"), texto(sel["descricao"]), height=80)
            st.caption(t(f"{AREA}.aviso_vendedor"))
            if st.form_submit_button(t("comum.salvar_alteracoes"), type="primary"):
                executar(dados_regioes.atualizar, id_, nome.strip(), int(vendedor),
                         opcional(descricao), sucesso=t(f"{AREA}.atualizado"))
        form_excluir(AREA, id_, dados_regioes.excluir, t(f"{AREA}.excluido"),
                     ao_sucesso=lambda: limpar_selecao("regioes"),
                     ajuda=ajuda("tooltips.excluir.regiao"))

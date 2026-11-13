"""Cadastro de vendedores: tabela com busca à esquerda, formulário à direita."""

import streamlit as st

from componentes.acoes import carregar, executar
from componentes.dicas import ajuda
from componentes.cadastro import cabecalho_edicao, form_excluir, lista_com_busca
from componentes.layout import painel, titulo_html
from componentes.tabela import limpar_selecao
from dados import vendedores as dados_vendedores
from util.formatacao import opcional, texto
from util.i18n import t

AREA = "cadastros.vendedores"


def render() -> None:
    df = carregar(dados_vendedores.listar)
    esquerda, direita = st.columns([3, 2])
    with esquerda:
        sel = lista_com_busca("vendedores", t(f"{AREA}.titulo"), df,
                              {"id_vendedor": t("comum.codigo"), "nome": t("comum.nome"),
                               "telefone": t("comum.telefone"), "email": t("comum.email"),
                               "comissao_fixa": t(f"{AREA}.col_comissao")},
                              percentual=("comissao_fixa",),
                              coluna_id="id_vendedor")

    with direita, painel("form_vendedores"):
        if sel is None:
            st.html(titulo_html(t(f"{AREA}.novo")))
            with st.form("vendedor_incluir", clear_on_submit=True):
                nome = st.text_input(t(f"{AREA}.campo_nome"))
                comissao = st.number_input(t(f"{AREA}.campo_comissao"), 0.0, 100.0, 5.0, 0.5, "%.2f")
                c1, c2 = st.columns(2)
                telefone = c1.text_input(t("comum.telefone"))
                email = c2.text_input(t("comum.email"))
                if st.form_submit_button(t(f"{AREA}.botao_cadastrar"), type="primary"):
                    executar(dados_vendedores.cadastrar, nome.strip(), comissao, opcional(telefone),
                             opcional(email), sucesso=t(f"{AREA}.cadastrado"))
            return

        id_ = int(sel["id_vendedor"])
        cabecalho_edicao("vendedores", t(f"{AREA}.editar", id=id_), texto(sel["nome"]), ajuda=ajuda("tooltips.novo"))
        with st.form(f"vendedor_editar_{id_}"):
            nome = st.text_input(t(f"{AREA}.campo_nome"), texto(sel["nome"]))
            comissao = st.number_input(t(f"{AREA}.campo_comissao"), 0.0, 100.0,
                                       float(sel["comissao_fixa"]), 0.5, "%.2f")
            c1, c2 = st.columns(2)
            telefone = c1.text_input(t("comum.telefone"), texto(sel["telefone"]))
            email = c2.text_input(t("comum.email"), texto(sel["email"]))
            st.caption(t(f"{AREA}.aviso_comissao"))
            if st.form_submit_button(t("comum.salvar_alteracoes"), type="primary"):
                executar(dados_vendedores.atualizar, id_, nome.strip(), comissao,
                         opcional(telefone), opcional(email), sucesso=t(f"{AREA}.atualizado"))
        form_excluir(AREA, id_, dados_vendedores.excluir, t(f"{AREA}.excluido"),
                     ao_sucesso=lambda: limpar_selecao("vendedores"),
                     ajuda=ajuda("tooltips.excluir.vendedor"))

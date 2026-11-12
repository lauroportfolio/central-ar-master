"""Cadastro de vendedores: tabela com busca à esquerda, formulário à direita."""

import streamlit as st

from componentes.acoes import carregar, executar
from componentes.cadastro import cabecalho_edicao, form_excluir, lista_com_busca
from componentes.layout import painel, titulo_html
from componentes.tabela import limpar_selecao
from dados import vendedores as dados_vendedores
from util.formatacao import opcional, texto


def render() -> None:
    df = carregar(dados_vendedores.listar)
    esquerda, direita = st.columns([3, 2])
    with esquerda:
        sel = lista_com_busca("vendedores", "Vendedores", df,
                              {"id_vendedor": "Código", "nome": "Nome", "telefone": "Telefone",
                               "email": "E-mail", "comissao_fixa": "Comissão padrão"},
                              percentual=("comissao_fixa",))

    with direita, painel("form_vendedores"):
        if sel is None:
            st.html(titulo_html("Novo vendedor"))
            with st.form("vendedor_incluir", clear_on_submit=True):
                nome = st.text_input("Nome *")
                comissao = st.number_input("Comissão padrão (%) *", 0.0, 100.0, 5.0, 0.5, "%.2f")
                c1, c2 = st.columns(2)
                telefone = c1.text_input("Telefone")
                email = c2.text_input("E-mail")
                if st.form_submit_button("Cadastrar vendedor", type="primary"):
                    executar(dados_vendedores.cadastrar, nome.strip(), comissao, opcional(telefone),
                             opcional(email), sucesso="Vendedor cadastrado (código {id}).")
            return

        id_ = int(sel["id_vendedor"])
        cabecalho_edicao("vendedores", f"Editar vendedor {id_}", texto(sel["nome"]))
        with st.form(f"vendedor_editar_{id_}"):
            nome = st.text_input("Nome *", texto(sel["nome"]))
            comissao = st.number_input("Comissão padrão (%) *", 0.0, 100.0,
                                       float(sel["comissao_fixa"]), 0.5, "%.2f")
            c1, c2 = st.columns(2)
            telefone = c1.text_input("Telefone", texto(sel["telefone"]))
            email = c2.text_input("E-mail", texto(sel["email"]))
            st.caption("Mudar a comissão padrão vale para pedidos novos; "
                       "pedidos já feitos guardam o próprio percentual.")
            if st.form_submit_button("Salvar alterações", type="primary"):
                executar(dados_vendedores.atualizar, id_, nome.strip(), comissao,
                         opcional(telefone), opcional(email), sucesso="Vendedor atualizado.")
        form_excluir("vendedor", id_, dados_vendedores.excluir, "Vendedor excluído.",
                     ao_sucesso=lambda: limpar_selecao("vendedores"))

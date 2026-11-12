"""Cadastro de clientes."""

import streamlit as st

from componentes.acoes import carregar, executar
from componentes.cadastro import cabecalho_edicao, form_excluir, lista_com_busca
from componentes.layout import painel, titulo_html
from componentes.tabela import limpar_selecao
from dados import clientes as dados_clientes
from dados import regioes as dados_regioes
from util.formatacao import opcional, so_digitos, texto


def render() -> None:
    df = carregar(dados_clientes.listar)
    regioes = carregar(dados_regioes.listar)
    esquerda, direita = st.columns([3, 2])
    with esquerda:
        sel = lista_com_busca("clientes", "Clientes", df,
                              {"id_cliente": "Código", "nome": "Nome", "cpf_cnpj": "CPF/CNPJ",
                               "telefone": "Telefone", "email": "E-mail", "endereco": "Endereço",
                               "regiao": "Região", "vendedor": "Vendedor"})

    with direita, painel("form_clientes"):
        if regioes.empty:
            st.info("Cadastre uma região antes de cadastrar clientes.")
            return
        ids_regioes = list(regioes["id_regiao"])
        info_regiao = {r.id_regiao: f"{r.nome} (vendedor: {r.vendedor})" for r in regioes.itertuples()}

        if sel is None:
            st.html(titulo_html("Novo cliente"))
            with st.form("cliente_incluir", clear_on_submit=True):
                nome = st.text_input("Nome / razão social *")
                c1, c2 = st.columns(2)
                cpf = c1.text_input("CPF/CNPJ * (somente números)", max_chars=18)
                telefone = c2.text_input("Telefone")
                email = st.text_input("E-mail")
                endereco = st.text_input("Endereço")
                regiao = st.selectbox("Região *", ids_regioes, format_func=info_regiao.get)
                if st.form_submit_button("Cadastrar cliente", type="primary"):
                    executar(dados_clientes.cadastrar, nome.strip(), so_digitos(cpf), int(regiao),
                             opcional(telefone), opcional(email), opcional(endereco),
                             sucesso="Cliente cadastrado (código {id}).")
            return

        id_ = int(sel["id_cliente"])
        cabecalho_edicao("clientes", f"Editar cliente {id_}", texto(sel["nome"]))
        with st.form(f"cliente_editar_{id_}"):
            nome = st.text_input("Nome / razão social *", texto(sel["nome"]))
            c1, c2 = st.columns(2)
            cpf = c1.text_input("CPF/CNPJ * (somente números)", texto(sel["cpf_cnpj"]), max_chars=18)
            telefone = c2.text_input("Telefone", texto(sel["telefone"]))
            email = st.text_input("E-mail", texto(sel["email"]))
            endereco = st.text_input("Endereço", texto(sel["endereco"]))
            regiao = st.selectbox("Região *", ids_regioes, format_func=info_regiao.get,
                                  index=ids_regioes.index(sel["id_regiao"]))
            if st.form_submit_button("Salvar alterações", type="primary"):
                executar(dados_clientes.atualizar, id_, nome.strip(), so_digitos(cpf), int(regiao),
                         opcional(telefone), opcional(email), opcional(endereco),
                         sucesso="Cliente atualizado.")
        form_excluir("cliente", id_, dados_clientes.excluir, "Cliente excluído.",
                     ao_sucesso=lambda: limpar_selecao("clientes"))

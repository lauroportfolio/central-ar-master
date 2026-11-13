"""Cadastro de clientes."""

import streamlit as st

from componentes.acoes import carregar, executar
from componentes.dicas import ajuda
from componentes.cadastro import cabecalho_edicao, form_excluir, lista_com_busca
from componentes.layout import painel, titulo_html
from componentes.tabela import limpar_selecao
from dados import clientes as dados_clientes
from dados import regioes as dados_regioes
from util.formatacao import opcional, so_digitos, texto
from util.i18n import t

AREA = "cadastros.clientes"


def render() -> None:
    df = carregar(dados_clientes.listar)
    regioes = carregar(dados_regioes.listar)
    esquerda, direita = st.columns([3, 2])
    with esquerda:
        sel = lista_com_busca("clientes", t(f"{AREA}.titulo"), df,
                              {"id_cliente": t("comum.codigo"), "nome": t("comum.nome"),
                               "cpf_cnpj": t("comum.cpf_cnpj"), "telefone": t("comum.telefone"),
                               "email": t("comum.email"), "endereco": t("comum.endereco"),
                               "regiao": t("comum.regiao"), "vendedor": t("comum.vendedor")},
                              coluna_id="id_cliente")

    with direita, painel("form_clientes"):
        if regioes.empty:
            st.info(t(f"{AREA}.sem_regioes"))
            return
        ids_regioes = list(regioes["id_regiao"])
        info_regiao = {r.id_regiao: t(f"{AREA}.opcao_regiao", regiao=r.nome, vendedor=r.vendedor)
                       for r in regioes.itertuples()}

        if sel is None:
            st.html(titulo_html(t(f"{AREA}.novo")))
            with st.form("cliente_incluir", clear_on_submit=True):
                nome = st.text_input(t(f"{AREA}.campo_nome"))
                c1, c2 = st.columns(2)
                cpf = c1.text_input(t(f"{AREA}.campo_cpf"), max_chars=18)
                telefone = c2.text_input(t("comum.telefone"))
                email = st.text_input(t("comum.email"))
                endereco = st.text_input(t("comum.endereco"))
                regiao = st.selectbox(t(f"{AREA}.campo_regiao"), ids_regioes, format_func=info_regiao.get,
                                      key="cliente_incluir_regiao")
                if st.form_submit_button(t(f"{AREA}.botao_cadastrar"), type="primary"):
                    executar(dados_clientes.cadastrar, nome.strip(), so_digitos(cpf), int(regiao),
                             opcional(telefone), opcional(email), opcional(endereco),
                             sucesso=t(f"{AREA}.cadastrado"))
            return

        id_ = int(sel["id_cliente"])
        cabecalho_edicao("clientes", t(f"{AREA}.editar", id=id_), texto(sel["nome"]), ajuda=ajuda("tooltips.novo"))
        with st.form(f"cliente_editar_{id_}"):
            nome = st.text_input(t(f"{AREA}.campo_nome"), texto(sel["nome"]))
            c1, c2 = st.columns(2)
            cpf = c1.text_input(t(f"{AREA}.campo_cpf"), texto(sel["cpf_cnpj"]), max_chars=18)
            telefone = c2.text_input(t("comum.telefone"), texto(sel["telefone"]))
            email = st.text_input(t("comum.email"), texto(sel["email"]))
            endereco = st.text_input(t("comum.endereco"), texto(sel["endereco"]))
            regiao = st.selectbox(t(f"{AREA}.campo_regiao"), ids_regioes, format_func=info_regiao.get,
                                  index=ids_regioes.index(sel["id_regiao"]), key=f"cliente_editar_regiao_{id_}")
            if st.form_submit_button(t("comum.salvar_alteracoes"), type="primary"):
                executar(dados_clientes.atualizar, id_, nome.strip(), so_digitos(cpf), int(regiao),
                         opcional(telefone), opcional(email), opcional(endereco),
                         sucesso=t(f"{AREA}.atualizado"))
        form_excluir(AREA, id_, dados_clientes.excluir, t(f"{AREA}.excluido"),
                     ao_sucesso=lambda: limpar_selecao("clientes"),
                     ajuda=ajuda("tooltips.excluir.cliente"))

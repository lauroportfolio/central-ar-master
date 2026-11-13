"""Cadastro de regiões (região fechada: um único vendedor por região)."""

import pandas as pd
import streamlit as st

from componentes.acoes import carregar, executar
from componentes.cadastro import cabecalho_edicao, form_excluir, lista_com_busca
from componentes.layout import painel, titulo_html
from componentes.tabela import limpar_selecao
from dados import regioes as dados_regioes
from dados import vendedores as dados_vendedores
from util.formatacao import opcional, texto


def _rotulo_por_id(df: pd.DataFrame, coluna_id: str, coluna_nome: str):
    nomes = dict(zip(df[coluna_id], df[coluna_nome]))
    return lambda i: f"{i} — {nomes.get(i, '')}"


def render() -> None:
    df = carregar(dados_regioes.listar)
    vendedores = carregar(dados_vendedores.listar)
    esquerda, direita = st.columns([3, 2])
    with esquerda:
        sel = lista_com_busca("regioes", "Regiões", df,
                              {"id_regiao": "Código", "nome": "Região", "descricao": "Descrição",
                               "vendedor": "Vendedor responsável", "qtd_clientes": "Clientes"})

    with direita, painel("form_regioes"):
        if vendedores.empty:
            st.info("Cadastre um vendedor antes de criar regiões.")
            return
        nome_vendedor = _rotulo_por_id(vendedores, "id_vendedor", "nome")
        ids_vendedores = list(vendedores["id_vendedor"])

        if sel is None:
            st.html(titulo_html("Nova região", "Região fechada: cada região tem um único vendedor."))
            with st.form("regiao_incluir", clear_on_submit=True):
                nome = st.text_input("Nome da região *")
                vendedor = st.selectbox("Vendedor responsável *", ids_vendedores, format_func=nome_vendedor,
                                        key="regiao_incluir_vendedor")
                descricao = st.text_area("Descrição (bairros, cidades...)", height=80)
                if st.form_submit_button("Cadastrar região", type="primary"):
                    executar(dados_regioes.cadastrar, nome.strip(), int(vendedor), opcional(descricao),
                             sucesso="Região cadastrada (código {id}).")
            return

        id_ = int(sel["id_regiao"])
        cabecalho_edicao("regioes", f"Editar região {id_}", texto(sel["nome"]))
        with st.form(f"regiao_editar_{id_}"):
            nome = st.text_input("Nome da região *", texto(sel["nome"]))
            vendedor = st.selectbox("Vendedor responsável *", ids_vendedores, format_func=nome_vendedor,
                                    index=ids_vendedores.index(sel["id_vendedor"]), key=f"regiao_editar_vendedor_{id_}")
            descricao = st.text_area("Descrição", texto(sel["descricao"]), height=80)
            st.caption("Trocar o vendedor vale para pedidos novos; "
                       "pedidos antigos continuam com quem fez a venda.")
            if st.form_submit_button("Salvar alterações", type="primary"):
                executar(dados_regioes.atualizar, id_, nome.strip(), int(vendedor),
                         opcional(descricao), sucesso="Região atualizada.")
        form_excluir("região", id_, dados_regioes.excluir, "Região excluída.",
                     ao_sucesso=lambda: limpar_selecao("regioes"))

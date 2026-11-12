"""Cadastro de produtos (o estoque baixa sozinho pela trigger do banco)."""

import streamlit as st

from componentes.acoes import carregar, executar
from componentes.cadastro import cabecalho_edicao, form_excluir, lista_com_busca
from componentes.layout import painel, titulo_html
from componentes.tabela import limpar_selecao
from dados import produtos as dados_produtos
from util.formatacao import texto


def render() -> None:
    df = carregar(dados_produtos.listar)
    esquerda, direita = st.columns([3, 2])
    with esquerda:
        sel = lista_com_busca("produtos", "Produtos", df,
                              {"id_produto": "Código", "descricao": "Descrição", "preco": "Preço",
                               "estoque": "Estoque"}, moeda=("preco",), quantidade=("estoque",))

    with direita, painel("form_produtos"):
        if sel is None:
            st.html(titulo_html("Novo produto"))
            with st.form("produto_incluir", clear_on_submit=True):
                descricao = st.text_input("Descrição *")
                c1, c2 = st.columns(2)
                preco = c1.number_input("Preço (R$) *", 0.0, None, 0.0, 10.0, "%.2f")
                estoque = c2.number_input("Estoque *", 0.0, None, 0.0, 1.0, "%.3f")
                if st.form_submit_button("Cadastrar produto", type="primary"):
                    executar(dados_produtos.cadastrar, descricao.strip(), preco, estoque,
                             sucesso="Produto cadastrado (código {id}).")
            return

        id_ = int(sel["id_produto"])
        cabecalho_edicao("produtos", f"Editar produto {id_}", texto(sel["descricao"]))
        with st.form(f"produto_editar_{id_}"):
            descricao = st.text_input("Descrição *", texto(sel["descricao"]))
            c1, c2 = st.columns(2)
            preco = c1.number_input("Preço (R$) *", 0.0, None, float(sel["preco"]), 10.0, "%.2f")
            estoque = c2.number_input("Estoque *", 0.0, None, float(sel["estoque"]), 1.0, "%.3f")
            st.caption("O estoque baixa sozinho quando um item é vendido (trigger no banco). "
                       "Mudar o preço não altera pedidos já feitos.")
            if st.form_submit_button("Salvar alterações", type="primary"):
                executar(dados_produtos.atualizar, id_, descricao.strip(), preco, estoque,
                         sucesso="Produto atualizado.")
        form_excluir("produto", id_, dados_produtos.excluir, "Produto excluído.",
                     ao_sucesso=lambda: limpar_selecao("produtos"))

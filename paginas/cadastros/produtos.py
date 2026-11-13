"""Cadastro de produtos (o estoque baixa sozinho pela trigger do banco)."""

import streamlit as st

from componentes.acoes import carregar, executar
from componentes.dicas import ajuda
from componentes.cadastro import cabecalho_edicao, form_excluir, lista_com_busca
from componentes.layout import painel, titulo_html
from componentes.tabela import limpar_selecao
from dados import produtos as dados_produtos
from util.formatacao import texto
from util.i18n import t

AREA = "cadastros.produtos"


def render() -> None:
    df = carregar(dados_produtos.listar)
    esquerda, direita = st.columns([3, 2])
    with esquerda:
        sel = lista_com_busca("produtos", t(f"{AREA}.titulo"), df,
                              {"id_produto": t("comum.codigo"), "descricao": t("comum.descricao"),
                               "preco": t("comum.preco"), "estoque": t("comum.estoque")},
                              moeda=("preco",), quantidade=("estoque",),
                              ajudas={"estoque": ajuda("tooltips.produtos.estoque")},
                              coluna_id="id_produto")

    with direita, painel("form_produtos"):
        if sel is None:
            st.html(titulo_html(t(f"{AREA}.novo")))
            with st.form("produto_incluir", clear_on_submit=True):
                descricao = st.text_input(t(f"{AREA}.campo_descricao"))
                c1, c2 = st.columns(2)
                preco = c1.number_input(t(f"{AREA}.campo_preco"), 0.0, None, 0.0, 10.0, "%.2f")
                estoque = c2.number_input(t(f"{AREA}.campo_estoque"), 0.0, None, 0.0, 1.0, "%.3f",
                                          help=ajuda("tooltips.produtos.estoque"))
                if st.form_submit_button(t(f"{AREA}.botao_cadastrar"), type="primary"):
                    executar(dados_produtos.cadastrar, descricao.strip(), preco, estoque,
                             sucesso=t(f"{AREA}.cadastrado"))
            return

        id_ = int(sel["id_produto"])
        cabecalho_edicao("produtos", t(f"{AREA}.editar", id=id_), texto(sel["descricao"]), ajuda=ajuda("tooltips.novo"))
        with st.form(f"produto_editar_{id_}"):
            descricao = st.text_input(t(f"{AREA}.campo_descricao"), texto(sel["descricao"]))
            c1, c2 = st.columns(2)
            preco = c1.number_input(t(f"{AREA}.campo_preco"), 0.0, None, float(sel["preco"]), 10.0, "%.2f")
            estoque = c2.number_input(t(f"{AREA}.campo_estoque"), 0.0, None, float(sel["estoque"]), 1.0, "%.3f",
                                      help=ajuda("tooltips.produtos.estoque"))
            st.caption(t(f"{AREA}.aviso_estoque"))
            if st.form_submit_button(t("comum.salvar_alteracoes"), type="primary"):
                executar(dados_produtos.atualizar, id_, descricao.strip(), preco, estoque,
                         sucesso=t(f"{AREA}.atualizado"))
        form_excluir(AREA, id_, dados_produtos.excluir, t(f"{AREA}.excluido"),
                     ao_sucesso=lambda: limpar_selecao("produtos"),
                     ajuda=ajuda("tooltips.excluir.produto"))

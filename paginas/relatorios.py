"""Tela Relatórios: uma aba por relatório, gráfico de um lado e tabela do outro."""

import streamlit as st

from componentes.acoes import carregar
from componentes.grafico import grafico_barras
from componentes.layout import lado_a_lado, painel, titulo_html
from componentes.tabela import tabela
from dados import regioes as dados_regioes
from dados import relatorios as dados_relatorios
from dados import vendedores as dados_vendedores
from util.formatacao import brl


def render() -> None:
    with painel("relatorios"):
        abas = st.tabs(["Por região", "Por cliente", "Por vendedor", "Clientes de uma região",
                        "Por produto", "Comissão por vendedor"], height="stretch")

        with abas[0]:
            df = carregar(dados_relatorios.vendas_por_regiao)
            graf, tab = lado_a_lado("regiao")
            with graf:
                st.metric("Total geral", brl(df["total_vendido"].sum() if not df.empty else 0))
                grafico_barras(df, "regiao", "total_vendido", "Região")
            with tab:
                tabela(df, {"regiao": "Região", "vendedor_responsavel": "Vendedor responsável",
                            "qtd_pedidos": "Pedidos", "total_vendido": "Total vendido"},
                       moeda=("total_vendido",))

        with abas[1]:
            df = carregar(dados_relatorios.vendas_por_cliente)
            graf, tab = lado_a_lado("cliente")
            with graf:
                grafico_barras(df, "cliente", "total_vendido", "Cliente", "Total comprado (R$)")
            with tab:
                tabela(df, {"cliente": "Cliente", "qtd_pedidos": "Pedidos",
                            "total_vendido": "Total comprado", "regiao": "Região",
                            "cpf_cnpj": "CPF/CNPJ"},
                       moeda=("total_vendido",))

        with abas[2]:
            df = carregar(dados_relatorios.vendas_por_vendedor)
            graf, tab = lado_a_lado("vendedor")
            with graf:
                grafico_barras(df, "vendedor", "total_vendido", "Vendedor")
            with tab:
                tabela(df, {"vendedor": "Vendedor", "qtd_pedidos": "Pedidos",
                            "total_vendido": "Total vendido", "total_comissao": "Comissão total"},
                       moeda=("total_vendido", "total_comissao"))

        with abas[3]:
            _clientes_de_uma_regiao()

        with abas[4]:
            df = carregar(dados_relatorios.vendas_por_produto)
            graf, tab = lado_a_lado("produto")
            with graf:
                grafico_barras(df, "produto", "total_vendido", "Produto")
            with tab:
                tabela(df, {"produto": "Produto", "qtd_pedidos": "Pedidos",
                            "quantidade_vendida": "Qtd vendida", "total_vendido": "Total vendido"},
                       moeda=("total_vendido",), quantidade=("quantidade_vendida",))

        with abas[5]:
            _comissao_por_vendedor()


def _clientes_de_uma_regiao() -> None:
    regioes = carregar(dados_regioes.listar)
    graf, tab = lado_a_lado("clientes_regiao")
    if regioes.empty:
        graf.info("Nenhuma região cadastrada.")
        return
    reg = regioes.set_index("id_regiao")
    with graf:
        id_regiao = st.selectbox("Região *", list(reg.index), index=None,
                                 placeholder="Escolha a região",
                                 format_func=lambda i: f"{reg.loc[i, 'nome']} (vendedor: {reg.loc[i, 'vendedor']})")
    if id_regiao is None:
        graf.info("Escolha uma região para ver os clientes.")
        return
    df = carregar(dados_relatorios.clientes_por_regiao, int(id_regiao))
    with graf:
        c1, c2 = st.columns(2)
        c1.metric("Clientes", len(df))
        c2.metric("Total comprado", brl(df["total_vendido"].sum() if not df.empty else 0))
        if not df.empty:
            grafico_barras(df, "cliente", "total_vendido", "Cliente", "Total comprado (R$)")
    with tab:
        tabela(df, {"cliente": "Cliente", "qtd_pedidos": "Pedidos", "total_vendido": "Total comprado",
                    "telefone": "Telefone", "cpf_cnpj": "CPF/CNPJ", "email": "E-mail",
                    "endereco": "Endereço"},
               moeda=("total_vendido",))


def _comissao_por_vendedor() -> None:
    vendedores = carregar(dados_vendedores.listar)
    nomes = dict(zip(vendedores["id_vendedor"], vendedores["nome"]))
    graf, tab = lado_a_lado("comissao", proporcao=(2, 3))
    with graf:
        id_vendedor = st.selectbox("Vendedor", [None, *nomes],
                                   format_func=lambda i: "Todos os vendedores" if i is None else nomes[i])
        st.caption("Comissão calculada item a item com o percentual gravado em cada pedido. "
                   "“% efetivo” = comissão ÷ total vendido do produto.")
    df = carregar(dados_relatorios.comissao_por_vendedor, None if id_vendedor is None else int(id_vendedor))
    if df.empty:
        graf.info("Nenhuma venda para este filtro.")
        return

    with graf:
        if id_vendedor is None:
            por_vendedor = df.groupby("vendedor", as_index=False)["valor_comissao"].sum()
            grafico_barras(por_vendedor, "vendedor", "valor_comissao", "Vendedor", "Comissão (R$)")
        else:
            grafico_barras(df, "produto", "valor_comissao", "Produto", "Comissão (R$)")

    with tab:
        for (_, nome), grupo in df.groupby(["id_vendedor", "vendedor"], sort=False):
            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 1, 1], vertical_alignment="center")
                c1.html(titulo_html(nome))
                c2.metric("Vendido", brl(grupo["total_vendido"].sum()))
                c3.metric("Comissão", brl(grupo["valor_comissao"].sum()))
                tabela(grupo, {"produto": "Produto", "qtd_pedidos": "Pedidos",
                               "quantidade_vendida": "Qtd", "total_vendido": "Total vendido",
                               "percentual_efetivo": "% efetivo", "valor_comissao": "Comissão"},
                       moeda=("total_vendido", "valor_comissao"), percentual=("percentual_efetivo",),
                       quantidade=("quantidade_vendida",), altura="auto",
                       larguras={"produto": 180, "qtd_pedidos": 62, "quantidade_vendida": 62})

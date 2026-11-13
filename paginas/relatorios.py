"""Tela Relatórios: uma aba por relatório, gráfico de um lado e tabela do outro."""

import streamlit as st

from componentes.acoes import carregar
from componentes.dicas import ajuda, icone_dica
from componentes.grafico import grafico_barras
from componentes.layout import lado_a_lado, painel, titulo_html
from componentes.tabela import tabela
from dados import regioes as dados_regioes
from dados import relatorios as dados_relatorios
from dados import vendedores as dados_vendedores
from util.formatacao import brl
from util.i18n import t

R = "relatorios"


def render() -> None:
    with painel("relatorios"):
        abas = st.tabs([t(f"{R}.abas.{aba}") for aba in
                        ("regiao", "cliente", "vendedor", "clientes_regiao", "produto", "comissao")],
                       height="stretch")

        with abas[0]:
            df = carregar(dados_relatorios.vendas_por_regiao)
            st.html(icone_dica("tooltips.relatorios.regiao"))
            graf, tab = lado_a_lado("regiao")
            with graf:
                st.metric(t(f"{R}.total_geral"), brl(df["total_vendido"].sum() if not df.empty else 0))
                grafico_barras(df, "regiao", "total_vendido", t("comum.regiao"))
            with tab:
                tabela(df, {"regiao": t("comum.regiao"), "vendedor_responsavel": t(f"{R}.col_vendedor_responsavel"),
                            "qtd_pedidos": t("comum.pedidos"), "total_vendido": t("comum.total_vendido")},
                       moeda=("total_vendido",), ajudas={"total_vendido": ajuda("tooltips.relatorios.total_vendido")})

        with abas[1]:
            df = carregar(dados_relatorios.vendas_por_cliente)
            st.html(icone_dica("tooltips.relatorios.cliente"))
            graf, tab = lado_a_lado("cliente")
            with graf:
                grafico_barras(df, "cliente", "total_vendido", t("comum.cliente"), t(f"{R}.eixo_total_comprado"))
            with tab:
                tabela(df, {"cliente": t("comum.cliente"), "qtd_pedidos": t("comum.pedidos"),
                            "total_vendido": t("comum.total_comprado"), "regiao": t("comum.regiao"),
                            "cpf_cnpj": t("comum.cpf_cnpj")},
                       moeda=("total_vendido",))

        with abas[2]:
            df = carregar(dados_relatorios.vendas_por_vendedor)
            st.html(icone_dica("tooltips.relatorios.vendedor"))
            graf, tab = lado_a_lado("vendedor")
            with graf:
                grafico_barras(df, "vendedor", "total_vendido", t("comum.vendedor"))
            with tab:
                tabela(df, {"vendedor": t("comum.vendedor"), "qtd_pedidos": t("comum.pedidos"),
                            "total_vendido": t("comum.total_vendido"), "total_comissao": t(f"{R}.col_comissao_total")},
                       moeda=("total_vendido", "total_comissao"),
                       ajudas={"total_vendido": ajuda("tooltips.relatorios.total_vendido"),
                               "total_comissao": ajuda("tooltips.relatorios.comissao_valor")})

        with abas[3]:
            _clientes_de_uma_regiao()

        with abas[4]:
            df = carregar(dados_relatorios.vendas_por_produto)
            st.html(icone_dica("tooltips.relatorios.produto"))
            graf, tab = lado_a_lado("produto")
            with graf:
                grafico_barras(df, "produto", "total_vendido", t("comum.produto"))
            with tab:
                tabela(df, {"produto": t("comum.produto"), "qtd_pedidos": t("comum.pedidos"),
                            "quantidade_vendida": t(f"{R}.col_qtd_vendida"), "total_vendido": t("comum.total_vendido")},
                       moeda=("total_vendido",), quantidade=("quantidade_vendida",),
                       ajudas={"total_vendido": ajuda("tooltips.relatorios.total_vendido")})

        with abas[5]:
            _comissao_por_vendedor()


def _clientes_de_uma_regiao() -> None:
    regioes = carregar(dados_regioes.listar)
    st.html(icone_dica("tooltips.relatorios.clientes_regiao"))
    graf, tab = lado_a_lado("clientes_regiao")
    if regioes.empty:
        graf.info(t(f"{R}.sem_regioes"))
        return
    reg = regioes.set_index("id_regiao")
    with graf:
        id_regiao = st.selectbox(t(f"{R}.campo_regiao"), list(reg.index), index=None,
                                 placeholder=t(f"{R}.escolha_regiao"),
                                 format_func=lambda i: t(f"{R}.opcao_regiao", regiao=reg.loc[i, "nome"],
                                                         vendedor=reg.loc[i, "vendedor"]),
                                 key="relatorio_regiao")
    if id_regiao is None:
        graf.info(t(f"{R}.aviso_regiao"))
        return
    df = carregar(dados_relatorios.clientes_por_regiao, int(id_regiao))
    with graf:
        c1, c2 = st.columns(2)
        c1.metric(t("comum.clientes"), len(df))
        c2.metric(t("comum.total_comprado"), brl(df["total_vendido"].sum() if not df.empty else 0))
        if not df.empty:
            grafico_barras(df, "cliente", "total_vendido", t("comum.cliente"), t(f"{R}.eixo_total_comprado"))
    with tab:
        tabela(df, {"cliente": t("comum.cliente"), "qtd_pedidos": t("comum.pedidos"),
                    "total_vendido": t("comum.total_comprado"), "telefone": t("comum.telefone"),
                    "cpf_cnpj": t("comum.cpf_cnpj"), "email": t("comum.email"), "endereco": t("comum.endereco")},
               moeda=("total_vendido",))


def _comissao_por_vendedor() -> None:
    vendedores = carregar(dados_vendedores.listar)
    nomes = dict(zip(vendedores["id_vendedor"], vendedores["nome"]))
    st.html(icone_dica("tooltips.relatorios.comissao"))
    graf, tab = lado_a_lado("comissao", proporcao=(2, 3))
    with graf:
        id_vendedor = st.selectbox(t(f"{R}.campo_vendedor"), [None, *nomes],
                                   format_func=lambda i: t(f"{R}.todos_vendedores") if i is None else nomes[i],
                                   key="relatorio_vendedor")
        st.caption(t(f"{R}.explicacao_comissao"))
    df = carregar(dados_relatorios.comissao_por_vendedor, None if id_vendedor is None else int(id_vendedor))
    if df.empty:
        graf.info(t(f"{R}.sem_vendas_filtro"))
        return

    with graf:
        if id_vendedor is None:
            por_vendedor = df.groupby("vendedor", as_index=False)["valor_comissao"].sum()
            grafico_barras(por_vendedor, "vendedor", "valor_comissao", t("comum.vendedor"), t(f"{R}.eixo_comissao"))
        else:
            grafico_barras(df, "produto", "valor_comissao", t("comum.produto"), t(f"{R}.eixo_comissao"))

    with tab:
        for (_, nome), grupo in df.groupby(["id_vendedor", "vendedor"], sort=False):
            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 1, 1], vertical_alignment="center")
                c1.html(titulo_html(nome))
                c2.metric(t(f"{R}.metrica_vendido"), brl(grupo["total_vendido"].sum()))
                c3.metric(t(f"{R}.metrica_comissao"), brl(grupo["valor_comissao"].sum()))
                tabela(grupo, {"produto": t("comum.produto"), "qtd_pedidos": t("comum.pedidos"),
                               "quantidade_vendida": t("comum.qtd"), "total_vendido": t("comum.total_vendido"),
                               "percentual_efetivo": t(f"{R}.col_pct_efetivo"), "valor_comissao": t("comum.comissao")},
                       moeda=("total_vendido", "valor_comissao"), percentual=("percentual_efetivo",),
                       quantidade=("quantidade_vendida",), altura="auto",
                       larguras={"produto": 180, "qtd_pedidos": 62, "quantidade_vendida": 62},
                       ajudas={"percentual_efetivo": ajuda("tooltips.relatorios.pct_efetivo"),
                               "valor_comissao": ajuda("tooltips.relatorios.comissao_valor")})

"""Tela Pedidos: lista à esquerda; à direita o pedido novo ou o selecionado."""

from __future__ import annotations

from datetime import date, datetime
from html import escape

import pandas as pd
import streamlit as st

from componentes.acoes import avisar, carregar, executar
from componentes.cadastro import form_excluir
from componentes.layout import painel, titulo_html
from componentes.tabela import filtrar, limpar_selecao, tabela, versao_selecao
from dados import clientes as dados_clientes
from dados import pedidos as dados_pedidos
from dados import produtos as dados_produtos
from util.erros import ErroBanco
from util.formatacao import brl, data_hora, pct, qtd, vazio


def render() -> None:
    pedidos = carregar(dados_pedidos.listar)
    clientes = carregar(dados_clientes.listar)
    produtos = carregar(dados_produtos.listar)

    esquerda, direita = st.columns([2, 3])
    with esquerda, painel("lista_pedidos"):
        c1, c2 = st.columns([3, 2], vertical_alignment="center")
        c1.html(titulo_html("Pedidos", f"{len(pedidos)} pedido(s) · clique para abrir"))
        c2.button("Novo pedido", icon=":material/add:", type="primary", width="stretch",
                  on_click=limpar_selecao, args=("pedidos",))
        termo = st.text_input("Buscar", placeholder="Buscar por cliente, vendedor, região...",
                              label_visibility="collapsed", key="busca_pedidos",
                              icon=":material/search:")
        visivel = filtrar(pedidos, termo).reset_index(drop=True)
        posicao = tabela(visivel, {"id_pedido": "Nº", "data_pedido": "Data", "cliente": "Cliente",
                                   "total_pedido": "Total"},
                         moeda=("total_pedido",), datas_curtas=("data_pedido",),
                         larguras={"id_pedido": 48},
                         chave=f"tabela_pedidos_{versao_selecao('pedidos')}_{termo}")

    with direita:
        if posicao is None or posicao >= len(visivel):
            _novo_pedido(clientes, produtos)
        else:
            _detalhe_pedido(int(visivel.iloc[posicao]["id_pedido"]), pedidos, clientes, produtos)


def _cabecalho_pedido(titulo: str, subtitulo: str | None = None):
    """Título à esquerda e TOTAL em destaque à direita. Devolve o espaço do total."""
    c1, c2 = st.columns([3, 2], vertical_alignment="center")
    c1.html(titulo_html(titulo, subtitulo))
    return c2.empty()


def _total_destaque(lugar, valor, rotulo: str = "Total do pedido") -> None:
    lugar.html(f'<div class="total-destaque"><span>{escape(rotulo)}</span>'
               f'<strong>{brl(valor)}</strong></div>')


# ----------------------------------------------------------------------------- Novo pedido

def _novo_pedido(clientes: pd.DataFrame, produtos: pd.DataFrame) -> None:
    with painel("pedido"):
        espaco_total = _cabecalho_pedido("Novo pedido", "O vendedor vem da região do cliente")
        with st.container(key="painel_pedido_corpo", height="stretch"):
            total = _corpo_novo_pedido(clientes, produtos)
        _total_destaque(espaco_total, total)


def _corpo_novo_pedido(clientes: pd.DataFrame, produtos: pd.DataFrame) -> float:
    if clientes.empty or produtos.empty:
        st.info("Cadastre pelo menos um cliente e um produto para lançar pedidos.")
        return 0.0

    versao = st.session_state.setdefault("_versao_novo_pedido", 0)
    cli = clientes.set_index("id_cliente")

    id_cliente = st.selectbox("Cliente *", list(cli.index), index=None,
                              placeholder="Escolha o cliente",
                              format_func=lambda i: f"{cli.loc[i, 'nome']} — {cli.loc[i, 'regiao']}",
                              key=f"novo_cliente_{versao}")
    if id_cliente is None:
        st.caption("Escolha o cliente para preencher o vendedor e a comissão.")
        return 0.0
    c = cli.loc[id_cliente]

    c1, c2, c3 = st.columns([2, 1, 1])
    c1.text_input("Vendedor (responsável pela região)", f"{c['vendedor']} — {c['regiao']}",
                  disabled=True)
    percentual = c2.number_input("Comissão deste pedido (%)", 0.0, 100.0,
                                 float(c["comissao_fixa"]), 0.5, "%.2f",
                                 key=f"novo_pct_{versao}_{id_cliente}",
                                 help="Começa com a comissão padrão do vendedor; pode ser alterada.")
    dia = c3.date_input("Data do pedido", date.today(), format="DD/MM/YYYY",
                        key=f"novo_data_{versao}")

    st.markdown("**Itens do pedido** — clique em ➕ embaixo da tabela para adicionar linhas")
    prod = produtos.set_index("id_produto")
    # A lista de produtos do editor fica "congelada" a partir do 1º item digitado.
    # Motivo: o st.data_editor com linhas dinâmicas é identificado também pelas opções das
    # colunas; se alguém cadastrar um produto enquanto o pedido é montado, a lista mudaria
    # e o Streamlit apagaria os itens já digitados. Com o editor vazio a lista é sempre a atual.
    chave_editor = f"novo_itens_{versao}"
    chave_opcoes = f"_opcoes_produtos_{versao}"
    editor_vazio = not (st.session_state.get(chave_editor) or {}).get("added_rows")
    if editor_vazio or chave_opcoes not in st.session_state:
        st.session_state[chave_opcoes] = {f"{i} — {prod.loc[i, 'descricao']}": int(i) for i in prod.index}
    rotulos = st.session_state[chave_opcoes]
    itens = st.data_editor(
        pd.DataFrame({"produto": pd.Series(dtype="object"), "quantidade": pd.Series(dtype="float"),
                      "preco_unitario": pd.Series(dtype="float"), "desconto": pd.Series(dtype="float")}),
        num_rows="dynamic", width="stretch", key=chave_editor,
        column_config={
            "produto": st.column_config.SelectboxColumn("Produto", options=list(rotulos),
                                                        required=True, width="large"),
            "quantidade": st.column_config.NumberColumn("Quantidade", min_value=0.001,
                                                        step=0.001, default=1.0, required=True),
            "preco_unitario": st.column_config.NumberColumn(
                "Preço unitário (R$)", min_value=0.0, step=0.01, format="%.2f",
                help="Deixe vazio para usar o preço atual do produto."),
            "desconto": st.column_config.NumberColumn("Desconto (%)", min_value=0.0, max_value=100.0,
                                                      step=0.5, default=0.0, format="%.2f"),
        },
    )

    linhas = []
    for r in itens.itertuples():
        if vazio(r.produto) or r.produto not in rotulos:
            continue
        id_produto = rotulos[r.produto]
        if id_produto not in prod.index:      # produto excluído enquanto o pedido era montado
            continue
        quantidade = 0.0 if vazio(r.quantidade) else float(r.quantidade)
        preco_informado = None if vazio(r.preco_unitario) else float(r.preco_unitario)
        preco = float(prod.loc[id_produto, "preco"]) if preco_informado is None else preco_informado
        desconto = 0.0 if vazio(r.desconto) else float(r.desconto)
        valor = round(quantidade * preco * (100 - desconto) / 100, 2)
        linhas.append({"fk_produto": id_produto, "produto": prod.loc[id_produto, "descricao"],
                       "quantidade": quantidade, "preco_unitario": preco_informado,
                       "preco": preco, "desconto": desconto, "valor": valor,
                       "estoque": float(prod.loc[id_produto, "estoque"])})

    total = sum(l["valor"] for l in linhas)
    comissao = sum(round(l["valor"] * percentual / 100, 2) for l in linhas)

    if linhas:
        resumo = pd.DataFrame(linhas)
        tabela(resumo, {"produto": "Produto", "quantidade": "Qtd", "preco": "Preço unit.",
                        "desconto": "Desconto", "valor": "Subtotal", "estoque": "Estoque atual"},
               moeda=("preco", "valor"), percentual=("desconto",), quantidade=("quantidade", "estoque"),
               altura="auto")

    c1, c2 = st.columns([3, 2], vertical_alignment="center")
    c1.caption(f"{len(linhas)} item(ns) · comissão do vendedor: **{brl(comissao)}**")
    salvar = c2.button("Salvar pedido", type="primary", icon="💾", disabled=not linhas,
                       width="stretch")
    if salvar:
        repetidos = {l["produto"] for l in linhas if sum(m["fk_produto"] == l["fk_produto"] for m in linhas) > 1}
        if repetidos:
            st.error(f"Produto repetido no pedido: {', '.join(repetidos)}. Junte numa linha só.", icon="🚫")
            return total
        momento = datetime.combine(dia, datetime.now().time().replace(microsecond=0))
        try:
            id_pedido = dados_pedidos.cadastrar_com_itens(int(id_cliente), int(c["id_vendedor"]),
                                                          percentual, momento, linhas)
        except ErroBanco as erro:
            st.error(str(erro), icon="🚫")
            return total
        st.session_state["_versao_novo_pedido"] = versao + 1
        avisar(f"Pedido nº {id_pedido} cadastrado — total {brl(total)}.")
        st.rerun()
    return total


# ----------------------------------------------------------------------------- Pedido selecionado

def _detalhe_pedido(sel: int, pedidos: pd.DataFrame, clientes: pd.DataFrame,
                    produtos: pd.DataFrame) -> None:
    ped = pedidos.set_index("id_pedido")
    p = ped.loc[sel]

    with painel("pedido"):
        espaco_total = _cabecalho_pedido(f"Pedido nº {sel}", data_hora(p["data_pedido"]))
        _total_destaque(espaco_total, p["total_pedido"])

        with st.container(key="painel_pedido_corpo", height="stretch"):
            st.html(
                '<div class="ficha">'
                f'<div><span>Cliente</span><b>{escape(str(p["cliente"]))}</b></div>'
                f'<div><span>Vendedor</span><b>{escape(str(p["vendedor"]))}</b></div>'
                f'<div><span>Região</span><b>{escape(str(p["regiao"]))}</b></div>'
                f'<div><span>Comissão</span><b>{pct(p["percentual_comissao"])} · '
                f'{brl(p["valor_comissao"])}</b></div>'
                '</div>')

            itens = carregar(dados_pedidos.listar_itens, int(sel))
            aba_itens, aba_incluir, aba_dados, aba_excluir = st.tabs(
                ["Itens", "Adicionar item", "Dados do pedido", "Excluir pedido"])

            prod = produtos.set_index("id_produto")

            with aba_itens:
                tabela(itens, {"produto": "Produto", "quantidade": "Qtd", "preco_unitario": "Preço unit.",
                               "desconto": "Desconto", "valor_total": "Subtotal"},
                       moeda=("preco_unitario", "valor_total"), percentual=("desconto",),
                       quantidade=("quantidade",), altura="auto")
                if not itens.empty:
                    it = itens.set_index("id_produto")
                    ids_itens = list(it.index)
                    id_item = st.selectbox("Alterar ou remover o item", ids_itens,
                                           format_func=lambda i: it.loc[i, "produto"],
                                           key=f"item_sel_{sel}")
                    atual = it.loc[id_item]
                    with st.form(f"item_editar_{sel}_{id_item}"):
                        c1, c2, c3 = st.columns(3)
                        quantidade = c1.number_input("Quantidade", 0.001, None, float(atual["quantidade"]),
                                                     1.0, "%.3f")
                        preco = c2.number_input("Preço unit. (R$)", 0.0, None,
                                                float(atual["preco_unitario"]), 10.0, "%.2f")
                        desconto = c3.number_input("Desconto (%)", 0.0, 100.0, float(atual["desconto"]),
                                                   0.5, "%.2f")
                        b1, b2 = st.columns(2)
                        salvar = b1.form_submit_button("Salvar item", type="primary")
                        remover = b2.form_submit_button("Remover item", icon="🗑️")
                        if salvar:
                            executar(dados_pedidos.atualizar_item, int(sel), int(id_item), quantidade,
                                     preco, desconto, sucesso="Item atualizado.")
                        if remover:
                            executar(dados_pedidos.excluir_item, int(sel), int(id_item),
                                     sucesso="Item removido (estoque devolvido).")

            with aba_incluir:
                no_pedido = set(itens["id_produto"]) if not itens.empty else set()
                disponiveis = [i for i in prod.index if i not in no_pedido]
                with st.form(f"item_incluir_{sel}", clear_on_submit=True):
                    if not disponiveis:
                        st.caption("Todos os produtos já estão neste pedido.")
                    id_produto = st.selectbox(
                        "Produto", disponiveis,
                        format_func=lambda i: f"{prod.loc[i, 'descricao']} — {brl(prod.loc[i, 'preco'])} "
                                              f"(estoque {qtd(prod.loc[i, 'estoque'])})",
                        key=f"item_incluir_produto_{sel}")
                    c1, c2, c3 = st.columns(3)
                    quantidade = c1.number_input("Quantidade", 0.001, None, 1.0, 1.0, "%.3f")
                    preco = c2.number_input("Preço unit. (R$)", 0.0, None, None, 10.0, "%.2f",
                                            placeholder="preço do produto")
                    desconto = c3.number_input("Desconto (%)", 0.0, 100.0, 0.0, 0.5, "%.2f")
                    if st.form_submit_button("Adicionar item", type="primary", disabled=not disponiveis):
                        executar(dados_pedidos.cadastrar_item, int(sel), int(id_produto), quantidade,
                                 preco, desconto, sucesso="Item adicionado ao pedido.")

            with aba_dados:
                cli = clientes.set_index("id_cliente")
                ids_clientes = list(cli.index)
                with st.form(f"pedido_editar_{sel}"):
                    id_cliente = st.selectbox(
                        "Cliente", ids_clientes, index=ids_clientes.index(p["id_cliente"]),
                        format_func=lambda i: f"{cli.loc[i, 'nome']} — {cli.loc[i, 'regiao']}",
                        key=f"pedido_editar_cliente_{sel}")
                    c1, c2 = st.columns(2)
                    percentual = c1.number_input("Comissão (%)", 0.0, 100.0,
                                                 float(p["percentual_comissao"]), 0.5, "%.2f")
                    dia = c2.date_input("Data", pd.Timestamp(p["data_pedido"]).date(), format="DD/MM/YYYY")
                    st.caption("Se trocar o cliente, o vendedor passa a ser o responsável pela região dele.")
                    if st.form_submit_button("Salvar dados do pedido", type="primary"):
                        vendedor = (int(p["id_vendedor"]) if id_cliente == p["id_cliente"]
                                    else int(cli.loc[id_cliente, "id_vendedor"]))
                        original = pd.Timestamp(p["data_pedido"]).to_pydatetime()
                        momento = datetime.combine(dia, original.time())
                        executar(dados_pedidos.atualizar, int(sel), int(id_cliente), vendedor, percentual,
                                 momento, sucesso=f"Pedido nº {sel} atualizado.")

            with aba_excluir:
                form_excluir("pedido", sel, dados_pedidos.excluir, f"Pedido nº {sel} excluído.",
                             aviso="Os itens também são apagados e o estoque deles é devolvido.",
                             ao_sucesso=lambda: limpar_selecao("pedidos"))

"""Tela Pedidos: lista à esquerda; à direita o pedido novo ou o selecionado."""

from __future__ import annotations

from datetime import date, datetime
from html import escape

import pandas as pd
import streamlit as st

from componentes.acoes import avisar, carregar, executar, mensagem_de_erro
from componentes.cadastro import form_excluir
from componentes.dicas import ajuda, com_dica, texto_cortado
from componentes.layout import painel, titulo_html
from componentes.tabela import (ESPACO_LISTA_PEDIDOS, ESPACO_PEDIDO, filtrar, larguras_editor, limpar_selecao,
                                tabela, tabela_selecionavel)
from dados import clientes as dados_clientes
from dados import pedidos as dados_pedidos
from dados import produtos as dados_produtos
from util.erros import ErroBanco
from util.formatacao import brl, data_hora, pct, qtd, vazio
from util.i18n import t

NOVO = "pedidos.novo"
DETALHE = "pedidos.detalhe"


def render() -> None:
    pedidos = carregar(dados_pedidos.listar)
    clientes = carregar(dados_clientes.listar)
    produtos = carregar(dados_produtos.listar)

    esquerda, direita = st.columns([2, 3])
    with esquerda, painel("lista_pedidos"):
        c1, c2 = st.columns([3, 2], vertical_alignment="center")
        c1.html(titulo_html(t("pedidos.titulo"), t("pedidos.subtitulo", n=len(pedidos))))
        c2.button(t("pedidos.botao_novo"), icon=":material/add:", type="primary", width="stretch",
                  on_click=limpar_selecao, args=("pedidos",))
        termo = st.text_input(t("comum.buscar"), placeholder=t("pedidos.buscar_placeholder"),
                              label_visibility="collapsed", key="busca_pedidos",
                              icon=":material/search:")
        visivel = filtrar(pedidos, termo).reset_index(drop=True)
        id_pedido = tabela_selecionavel("pedidos", visivel,
                                        {"id_pedido": t("pedidos.col_numero"), "data_pedido": t("comum.data"),
                                         "cliente": t("comum.cliente"), "total_pedido": t("comum.total")},
                                        "id_pedido", moeda=("total_pedido",), datas_curtas=("data_pedido",),
                                        espaco=ESPACO_LISTA_PEDIDOS,
                                        ajudas={"total_pedido": ajuda("tooltips.pedido.total")})

    with direita:
        if id_pedido is None:
            _novo_pedido(clientes, produtos)
        else:
            _detalhe_pedido(id_pedido, pedidos, clientes, produtos)


def _cabecalho_pedido(titulo: str, subtitulo: str | None = None):
    """Título à esquerda e TOTAL em destaque à direita. Devolve o espaço do total."""
    c1, c2 = st.columns([3, 2], vertical_alignment="center")
    c1.html(titulo_html(titulo, subtitulo))
    return c2.empty()


def _total_destaque(lugar, valor) -> None:
    lugar.html(f'<div class="total-destaque"><span>{escape(t("pedidos.total_do_pedido"))}</span>'
               f'<strong>{brl(valor)}</strong></div>')


# ----------------------------------------------------------------------------- Novo pedido

def _novo_pedido(clientes: pd.DataFrame, produtos: pd.DataFrame) -> None:
    with painel("pedido"):
        espaco_total = _cabecalho_pedido(t(f"{NOVO}.titulo"), t(f"{NOVO}.subtitulo"))
        with st.container(key="painel_pedido_corpo", height="stretch"):
            total = _corpo_novo_pedido(clientes, produtos)
        _total_destaque(espaco_total, total)


def _corpo_novo_pedido(clientes: pd.DataFrame, produtos: pd.DataFrame) -> float:
    if clientes.empty or produtos.empty:
        st.info(t(f"{NOVO}.sem_cadastros"))
        return 0.0

    versao = st.session_state.setdefault("_versao_novo_pedido", 0)
    cli = clientes.set_index("id_cliente")

    id_cliente = st.selectbox(t(f"{NOVO}.campo_cliente"), list(cli.index), index=None,
                              placeholder=t(f"{NOVO}.escolha_cliente"),
                              format_func=lambda i: t(f"{NOVO}.opcao_cliente", cliente=cli.loc[i, "nome"],
                                                      regiao=cli.loc[i, "regiao"]),
                              key=f"novo_cliente_{versao}")
    if id_cliente is None:
        st.caption(t(f"{NOVO}.aviso_cliente"))
        return 0.0
    c = cli.loc[id_cliente]

    c1, c2, c3 = st.columns([2, 1, 1])
    c1.text_input(t(f"{NOVO}.campo_vendedor"), f"{c['vendedor']} — {c['regiao']}", disabled=True)
    percentual = c2.number_input(t(f"{NOVO}.campo_comissao"), 0.0, 100.0,
                                 float(c["comissao_fixa"]), 0.5, "%.2f",
                                 key=f"novo_pct_{versao}_{id_cliente}", help=ajuda("tooltips.pedido.comissao"))
    dia = c3.date_input(t(f"{NOVO}.campo_data"), date.today(), format=t("formato.data_widget"),
                        key=f"novo_data_{versao}")

    st.markdown(t(f"{NOVO}.itens_titulo"))
    prod = produtos.set_index("id_produto")
    # A lista de produtos e as larguras das colunas do editor ficam "congeladas" a partir do
    # 1º item digitado. Motivo: o st.data_editor com linhas dinâmicas é identificado também
    # pelas opções das colunas; se alguém cadastrar um produto (ou a janela mudar de tamanho)
    # enquanto o pedido é montado, as opções mudariam e o Streamlit apagaria os itens já
    # digitados. Com o editor vazio, a lista e as larguras são sempre as atuais.
    chave_editor = f"novo_itens_{versao}"
    chave_opcoes = f"_opcoes_produtos_{versao}"
    chave_larguras = f"_larguras_itens_{versao}"
    rotulos_colunas = {"produto": t("comum.produto"), "quantidade": t("comum.quantidade"),
                       "preco_unitario": t(f"{NOVO}.col_preco_unitario"), "desconto": t(f"{NOVO}.col_desconto")}
    editor_vazio = not (st.session_state.get(chave_editor) or {}).get("added_rows")
    if editor_vazio or chave_opcoes not in st.session_state:
        st.session_state[chave_opcoes] = {f"{i} — {prod.loc[i, 'descricao']}": int(i) for i in prod.index}
        st.session_state[chave_larguras] = larguras_editor(rotulos_colunas, "produto", ESPACO_PEDIDO,
                                                           ajudas=("preco_unitario",))
    rotulos = st.session_state[chave_opcoes]
    largura = st.session_state[chave_larguras]
    itens = st.data_editor(
        pd.DataFrame({"produto": pd.Series(dtype="object"), "quantidade": pd.Series(dtype="float"),
                      "preco_unitario": pd.Series(dtype="float"), "desconto": pd.Series(dtype="float")}),
        num_rows="dynamic", width="stretch", key=chave_editor,
        column_config={
            "produto": st.column_config.SelectboxColumn(rotulos_colunas["produto"], options=list(rotulos),
                                                        required=True, width=largura["produto"]),
            "quantidade": st.column_config.NumberColumn(rotulos_colunas["quantidade"], min_value=0.001,
                                                        step=0.001, default=1.0, required=True,
                                                        width=largura["quantidade"]),
            "preco_unitario": st.column_config.NumberColumn(
                rotulos_colunas["preco_unitario"], min_value=0.0, step=0.01, format="%.2f",
                help=ajuda("tooltips.pedido.preco_unitario"), width=largura["preco_unitario"]),
            "desconto": st.column_config.NumberColumn(rotulos_colunas["desconto"], min_value=0.0,
                                                      max_value=100.0, step=0.5, default=0.0, format="%.2f",
                                                      width=largura["desconto"]),
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
        tabela(resumo, {"produto": t("comum.produto"), "quantidade": t("comum.qtd"),
                        "preco": t("comum.preco_unit"), "desconto": t("comum.desconto"),
                        "valor": t("comum.subtotal"), "estoque": t(f"{NOVO}.col_estoque_atual")},
               moeda=("preco", "valor"), percentual=("desconto",), quantidade=("quantidade", "estoque"),
               altura="auto", espaco=ESPACO_PEDIDO,
               ajudas={"estoque": ajuda("tooltips.pedido.estoque_atual"),
                                      "valor": ajuda("tooltips.pedido.subtotal")})

    c1, c2 = st.columns([3, 2], vertical_alignment="center")
    c1.caption(t(f"{NOVO}.rodape", n=len(linhas), comissao=brl(comissao)))
    salvar = c2.button(t(f"{NOVO}.botao_salvar"), type="primary", icon="💾", disabled=not linhas,
                       width="stretch")
    if salvar:
        repetidos = {l["produto"] for l in linhas if sum(m["fk_produto"] == l["fk_produto"] for m in linhas) > 1}
        if repetidos:
            st.error(t(f"{NOVO}.repetido", produtos=", ".join(repetidos)), icon="🚫")
            return total
        momento = datetime.combine(dia, datetime.now().time().replace(microsecond=0))
        try:
            id_pedido = dados_pedidos.cadastrar_com_itens(int(id_cliente), int(c["id_vendedor"]),
                                                          percentual, momento, linhas)
        except ErroBanco as erro:
            st.error(mensagem_de_erro(erro), icon="🚫")
            return total
        st.session_state["_versao_novo_pedido"] = versao + 1
        avisar(t(f"{NOVO}.cadastrado", id=id_pedido, total=brl(total)))
        st.rerun()
    return total


# ----------------------------------------------------------------------------- Pedido selecionado

def _detalhe_pedido(sel: int, pedidos: pd.DataFrame, clientes: pd.DataFrame,
                    produtos: pd.DataFrame) -> None:
    ped = pedidos.set_index("id_pedido")
    p = ped.loc[sel]

    with painel("pedido"):
        espaco_total = _cabecalho_pedido(t(f"{DETALHE}.titulo", id=sel), data_hora(p["data_pedido"]))
        _total_destaque(espaco_total, p["total_pedido"])

        with st.container(key="painel_pedido_corpo", height="stretch"):
            st.html(
                '<div class="ficha">'
                f'<div><span>{escape(t(f"{DETALHE}.ficha_cliente"))}</span><b>{texto_cortado(str(p["cliente"]))}</b></div>'
                f'<div><span>{escape(t(f"{DETALHE}.ficha_vendedor"))}</span><b>{texto_cortado(str(p["vendedor"]))}</b></div>'
                f'<div><span>{escape(t(f"{DETALHE}.ficha_regiao"))}</span><b>{texto_cortado(str(p["regiao"]))}</b></div>'
                + com_dica(f'<div><span>{escape(t(f"{DETALHE}.ficha_comissao"))}</span><b>{pct(p["percentual_comissao"])} · '
                           f'{brl(p["valor_comissao"])}</b></div>', "tooltips.pedido.comissao_valor", alinhamento="fim") +
                '</div>')

            itens = carregar(dados_pedidos.listar_itens, int(sel))
            aba_itens, aba_incluir, aba_dados, aba_excluir = st.tabs(
                [t(f"{DETALHE}.aba_itens"), t(f"{DETALHE}.aba_adicionar"),
                 t(f"{DETALHE}.aba_dados"), t(f"{DETALHE}.aba_excluir")])

            prod = produtos.set_index("id_produto")

            with aba_itens:
                tabela(itens, {"produto": t("comum.produto"), "quantidade": t("comum.qtd"),
                               "preco_unitario": t("comum.preco_unit"), "desconto": t("comum.desconto"),
                               "valor_total": t("comum.subtotal")},
                       moeda=("preco_unitario", "valor_total"), percentual=("desconto",),
                       quantidade=("quantidade",), altura="auto", espaco=ESPACO_PEDIDO,
                       ajudas={"valor_total": ajuda("tooltips.pedido.subtotal")})
                if not itens.empty:
                    it = itens.set_index("id_produto")
                    ids_itens = list(it.index)
                    id_item = st.selectbox(t(f"{DETALHE}.alterar_item"), ids_itens,
                                           format_func=lambda i: it.loc[i, "produto"],
                                           key=f"item_sel_{sel}")
                    atual = it.loc[id_item]
                    with st.form(f"item_editar_{sel}_{id_item}"):
                        c1, c2, c3 = st.columns(3)
                        quantidade = c1.number_input(t(f"{DETALHE}.campo_quantidade"), 0.001, None,
                                                     float(atual["quantidade"]), 1.0, "%.3f")
                        preco = c2.number_input(t(f"{DETALHE}.campo_preco"), 0.0, None,
                                                float(atual["preco_unitario"]), 10.0, "%.2f")
                        desconto = c3.number_input(t(f"{DETALHE}.campo_desconto"), 0.0, 100.0,
                                                   float(atual["desconto"]), 0.5, "%.2f")
                        b1, b2 = st.columns(2)
                        salvar = b1.form_submit_button(t(f"{DETALHE}.botao_salvar_item"), type="primary")
                        remover = b2.form_submit_button(t(f"{DETALHE}.botao_remover_item"), icon="🗑️",
                                                       help=ajuda("tooltips.excluir.item"))
                        if salvar:
                            executar(dados_pedidos.atualizar_item, int(sel), int(id_item), quantidade,
                                     preco, desconto, sucesso=t(f"{DETALHE}.item_atualizado"))
                        if remover:
                            executar(dados_pedidos.excluir_item, int(sel), int(id_item),
                                     sucesso=t(f"{DETALHE}.item_removido"))

            with aba_incluir:
                no_pedido = set(itens["id_produto"]) if not itens.empty else set()
                disponiveis = [i for i in prod.index if i not in no_pedido]
                with st.form(f"item_incluir_{sel}", clear_on_submit=True):
                    if not disponiveis:
                        st.caption(t(f"{DETALHE}.todos_no_pedido"))
                    id_produto = st.selectbox(
                        t(f"{DETALHE}.campo_produto"), disponiveis,
                        format_func=lambda i: t(f"{DETALHE}.opcao_produto", produto=prod.loc[i, "descricao"],
                                                preco=brl(prod.loc[i, "preco"]),
                                                estoque=qtd(prod.loc[i, "estoque"])),
                        key=f"item_incluir_produto_{sel}")
                    c1, c2, c3 = st.columns(3)
                    quantidade = c1.number_input(t(f"{DETALHE}.campo_quantidade"), 0.001, None, 1.0, 1.0, "%.3f")
                    preco = c2.number_input(t(f"{DETALHE}.campo_preco"), 0.0, None, None, 10.0, "%.2f",
                                            placeholder=t(f"{DETALHE}.preco_placeholder"),
                                            help=ajuda("tooltips.pedido.preco_unitario"))
                    desconto = c3.number_input(t(f"{DETALHE}.campo_desconto"), 0.0, 100.0, 0.0, 0.5, "%.2f")
                    if st.form_submit_button(t(f"{DETALHE}.botao_adicionar"), type="primary",
                                             disabled=not disponiveis):
                        executar(dados_pedidos.cadastrar_item, int(sel), int(id_produto), quantidade,
                                 preco, desconto, sucesso=t(f"{DETALHE}.item_adicionado"))

            with aba_dados:
                cli = clientes.set_index("id_cliente")
                ids_clientes = list(cli.index)
                with st.form(f"pedido_editar_{sel}"):
                    id_cliente = st.selectbox(
                        t(f"{DETALHE}.campo_cliente"), ids_clientes, index=ids_clientes.index(p["id_cliente"]),
                        format_func=lambda i: t(f"{NOVO}.opcao_cliente", cliente=cli.loc[i, "nome"],
                                                regiao=cli.loc[i, "regiao"]),
                        key=f"pedido_editar_cliente_{sel}")
                    c1, c2 = st.columns(2)
                    percentual = c1.number_input(t(f"{DETALHE}.campo_comissao"), 0.0, 100.0,
                                                 float(p["percentual_comissao"]), 0.5, "%.2f",
                                                 help=ajuda("tooltips.pedido.comissao"))
                    dia = c2.date_input(t(f"{DETALHE}.campo_data"), pd.Timestamp(p["data_pedido"]).date(),
                                        format=t("formato.data_widget"))
                    st.caption(t(f"{DETALHE}.aviso_troca_cliente"))
                    if st.form_submit_button(t(f"{DETALHE}.botao_salvar_dados"), type="primary"):
                        vendedor = (int(p["id_vendedor"]) if id_cliente == p["id_cliente"]
                                    else int(cli.loc[id_cliente, "id_vendedor"]))
                        original = pd.Timestamp(p["data_pedido"]).to_pydatetime()
                        momento = datetime.combine(dia, original.time())
                        executar(dados_pedidos.atualizar, int(sel), int(id_cliente), vendedor, percentual,
                                 momento, sucesso=t(f"{DETALHE}.atualizado", id=sel))

            with aba_excluir:
                form_excluir(DETALHE, sel, dados_pedidos.excluir, t(f"{DETALHE}.excluido", id=sel),
                             aviso=t(f"{DETALHE}.excluir_aviso"),
                             ao_sucesso=lambda: limpar_selecao("pedidos"), ajuda=ajuda("tooltips.excluir.pedido"))

"""Central de Ar Ltda. — sistema de vendas (Streamlit + SQL Server).

Toda leitura e gravação passa por stored procedures (ver db.py).
Layout: navbar no topo, faixa de status e painéis com scroll interno
(a página em si nunca rola — ver ui/estilo.css).
"""

from __future__ import annotations

import re
from datetime import date, datetime
from html import escape
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

import db

PASTA_UI = Path(__file__).parent / "ui"
COR_BARRA = "#1E6FD9"

st.set_page_config(page_title="Central de Ar Ltda.", page_icon="❄️", layout="wide")


# =============================================================================
# Formatação
# =============================================================================

def _vazio(v) -> bool:
    return v is None or (not isinstance(v, str) and pd.isna(v))


def _padrao_br(s: str) -> str:
    """1,234.56 -> 1.234,56"""
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def brl(v) -> str:
    return "" if _vazio(v) else "R$ " + _padrao_br(f"{float(v):,.2f}")


def brl_curto(v) -> str:
    """R$ 123,8 mil / R$ 1,2 mi"""
    v = float(v or 0)
    if v >= 1_000_000:
        return "R$ " + _padrao_br(f"{v / 1_000_000:.1f}") + " mi"
    if v >= 1_000:
        return "R$ " + _padrao_br(f"{v / 1_000:.1f}") + " mil"
    return brl(v)


def pct(v) -> str:
    return "" if _vazio(v) else _padrao_br(f"{float(v):.2f}") + "%"


def qtd(v) -> str:
    """Quantidades: 2 / 1,5 / 1.200"""
    if _vazio(v):
        return ""
    return _padrao_br(f"{float(v):,.3f}".rstrip("0").rstrip("."))


def data_hora(v) -> str:
    return "" if _vazio(v) else pd.Timestamp(v).strftime("%d/%m/%Y %H:%M")


def texto(v) -> str:
    return "" if _vazio(v) else str(v)


def opcional(s: str | None) -> str | None:
    s = (s or "").strip()
    return s or None


def so_digitos(s: str | None) -> str:
    return re.sub(r"\D", "", s or "")


# =============================================================================
# Utilitários de tela
# =============================================================================

def carregar(funcao, *args):
    """Lê dados do banco; se der erro, mostra a mensagem e para a página."""
    try:
        return funcao(*args)
    except db.ErroBanco as erro:
        st.error(f"Erro ao acessar o banco de dados: {erro}", icon="🚫")
        st.stop()


def executar(funcao, *args, sucesso: str, ao_sucesso=None, **kwargs) -> None:
    """Grava no banco. Erro (THROW do SQL Server) -> st.error com a mensagem do banco,
    dentro do painel do formulário (o painel rola; a página não)."""
    try:
        resultado = funcao(*args, **kwargs)
    except db.ErroBanco as erro:
        st.error(str(erro), icon="🚫")
        return
    if ao_sucesso:
        ao_sucesso()
    st.session_state["_aviso"] = sucesso.format(id=resultado)
    st.rerun()


def mostrar_aviso() -> None:
    """Mensagem de sucesso como toast (não ocupa espaço no layout)."""
    aviso = st.session_state.pop("_aviso", None)
    if aviso:
        st.toast(aviso, icon="✅", duration="long")


def painel(chave: str, titulo: str | None = None, subtitulo: str | None = None,
           borda: bool = True):
    """Cartão com scroll interno que ocupa a altura restante da janela."""
    caixa = st.container(key=f"painel_{chave}", border=borda, height="stretch")
    if titulo:
        caixa.html(titulo_html(titulo, subtitulo))
    return caixa


def titulo_html(titulo: str, subtitulo: str | None = None) -> str:
    html = f'<div class="painel-titulo">{escape(titulo)}</div>'
    if subtitulo:
        html += f'<div class="painel-subtitulo">{escape(subtitulo)}</div>'
    return html


def versao_selecao(chave: str) -> int:
    return st.session_state.setdefault(f"_versao_{chave}", 0)


def limpar_selecao(chave: str) -> None:
    """Desmarca a linha selecionada na tabela (troca o key do dataframe)."""
    st.session_state[f"_versao_{chave}"] = versao_selecao(chave) + 1


def filtrar(df: pd.DataFrame, termo: str | None) -> pd.DataFrame:
    termo = (termo or "").strip().casefold()
    if not termo or df.empty:
        return df
    achou = df.astype(str).apply(lambda col: col.str.casefold().str.contains(termo, regex=False))
    return df[achou.any(axis=1)]


def data_curta(v) -> str:
    return "" if _vazio(v) else pd.Timestamp(v).strftime("%d/%m/%Y")


def tabela(df: pd.DataFrame, colunas: dict[str, str], moeda=(), percentual=(),
           quantidade=(), datas=(), datas_curtas=(), altura="stretch", chave: str | None = None,
           larguras: dict[str, int] | None = None):
    """st.dataframe com cabeçalhos em português e valores formatados (R$, %, datas).
    Com `chave`, permite selecionar uma linha e devolve a posição dela (ou None).
    `larguras` fixa a largura (px) de colunas específicas, ex.: {"produto": 180}."""
    if df.empty:
        st.info("Nenhum registro encontrado.")
        return None
    visivel = df[list(colunas)].rename(columns=colunas)
    formatos = {}
    for grupo, funcao in ((moeda, brl), (percentual, pct), (quantidade, qtd), (datas, data_hora),
                          (datas_curtas, data_curta)):
        for coluna in grupo:
            formatos[colunas[coluna]] = funcao
    textos = [colunas[c] for c in colunas
              if c not in (*moeda, *percentual, *quantidade, *datas, *datas_curtas)
              and visivel[colunas[c]].dtype != "int64"]
    for coluna in textos:
        formatos.setdefault(coluna, texto)
    # Largura mínima para valores formatados não serem cortados ("R$ 2.84...")
    config_colunas = {}
    for grupo, px in ((moeda, 130), (datas, 135), (datas_curtas, 95), (percentual, 105),
                      (quantidade, 100)):
        for coluna in grupo:
            config_colunas[colunas[coluna]] = st.column_config.Column(width=px)
    for coluna, px in (larguras or {}).items():
        config_colunas[colunas[coluna]] = st.column_config.Column(width=px)
    selecao = {}
    if chave:
        selecao = {"on_select": "rerun", "selection_mode": "single-row", "key": chave}
    evento = st.dataframe(visivel.style.format(formatos), hide_index=True, width="stretch",
                          height=altura, column_config=config_colunas, **selecao)
    if chave and evento.selection.rows:
        return evento.selection.rows[0]
    return None


def grafico_barras(df: pd.DataFrame, categoria: str, valor: str, titulo_categoria: str,
                   titulo_valor: str = "Total vendido (R$)", preencher: bool = False) -> None:
    """Barras horizontais (uma série só), ordenadas do maior para o menor, com tooltip em R$.

    preencher=False: altura proporcional ao número de barras (o painel rola se precisar).
    preencher=True : ocupa a altura que sobra no painel; a espessura da barra é limitada
                     (no máximo 28 px e 60% da faixa de cada categoria), sem sobreposição.
    """
    dados = df[[categoria, valor]].copy()
    dados = dados[dados[valor] > 0]
    if dados.empty:
        st.caption("Sem vendas para mostrar no gráfico.")
        return
    dados["valor_formatado"] = dados[valor].map(brl)
    # Altura proporcional ao número de barras (32 px por categoria + eixo).
    # A altura é passada também ao st.altair_chart, senão o Streamlit encolhe o gráfico.
    altura = 32 * len(dados) + 56
    barra = {"size": alt.ExprRef("min(28, bandwidth('y') * 0.6)")} if preencher else {}
    grafico = (
        alt.Chart(dados, background="transparent")
        .mark_bar(color=COR_BARRA, cornerRadiusEnd=4, **barra)
        .encode(
            y=alt.Y(f"{categoria}:N", sort="-x", title=None,
                    scale=alt.Scale(paddingInner=0.3, paddingOuter=0.15),
                    axis=alt.Axis(labelLimit=220, labelOverlap=False)),
            x=alt.X(f"{valor}:Q", title=titulo_valor,
                    axis=alt.Axis(format="~s", grid=True, tickCount=6)),
            tooltip=[alt.Tooltip(f"{categoria}:N", title=titulo_categoria),
                     alt.Tooltip("valor_formatado:N", title=titulo_valor.replace(" (R$)", ""))],
        )
        .properties(height="container" if preencher else altura - 56)
        .configure_axis(gridOpacity=0.35, domain=False, tickColor="transparent")
        .configure_view(strokeWidth=0)
    )
    st.altair_chart(grafico, width="stretch", height="stretch" if preencher else altura)


def faixa_status() -> None:
    """Faixa abaixo da navbar: bolinha colorida + número + rótulo."""
    try:
        pedidos = db.listar_pedidos()
        vendedores = db.listar_vendedores()
        produtos = db.listar_produtos()
    except db.ErroBanco:
        st.html('<div class="faixa-status"><span class="item"><span class="ponto vermelho"></span>'
                '<b>Sem conexão com o banco</b></span></div>')
        return
    total = pedidos["total_pedido"].sum() if not pedidos.empty else 0
    baixo = int((produtos["estoque"] < 10).sum()) if not produtos.empty else 0
    itens = [
        ("verde", f"{len(pedidos)}", "pedidos" if len(pedidos) != 1 else "pedido"),
        ("azul", brl_curto(total), "vendidos"),
        ("amarelo", f"{len(vendedores)}", "vendedores" if len(vendedores) != 1 else "vendedor"),
    ]
    if baixo:
        itens.append(("vermelho", f"{baixo}",
                      "produto com estoque baixo" if baixo == 1 else "produtos com estoque baixo"))
    else:
        itens.append(("verde", "Estoque", "ok"))
    html = "".join(f'<span class="item"><span class="ponto {cor}"></span><b>{escape(num)}</b> {escape(rot)}</span>'
                   for cor, num, rot in itens)
    html += (f'<span class="banco">Banco <b>{escape(db.nome_banco())}</b> · '
             f'modo {escape(db.modo_conexao())}</span>')
    st.html(f'<div class="faixa-status">{html}</div>')


def form_excluir(entidade: str, id_, funcao, sucesso: str, aviso: str | None = None,
                 ao_sucesso=None) -> None:
    with st.form(f"{entidade}_excluir_{id_}"):
        st.markdown(f"**Excluir {entidade}**")
        if aviso:
            st.caption(aviso)
        confirma = st.checkbox(f"Confirmo que quero excluir este {entidade}")
        if st.form_submit_button(f"Excluir {entidade}", icon="🗑️"):
            if not confirma:
                st.warning("Marque a confirmação para excluir.")
            else:
                executar(funcao, int(id_), sucesso=sucesso, ao_sucesso=ao_sucesso)


# =============================================================================
# Início
# =============================================================================

def pagina_inicio() -> None:
    pedidos = carregar(db.listar_pedidos)
    vendedores = carregar(db.listar_vendedores)
    regioes = carregar(db.vendas_por_regiao)
    clientes = carregar(db.listar_clientes)
    produtos = carregar(db.listar_produtos)

    total = pedidos["total_pedido"].sum() if not pedidos.empty else 0
    comissoes = pedidos["valor_comissao"].sum() if not pedidos.empty else 0
    ticket = total / len(pedidos) if len(pedidos) else 0

    principal, lateral = st.columns([7, 3])

    with principal, painel("inicio", "Visão geral"):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total vendido", brl(total), border=True)
        c2.metric("Pedidos", len(pedidos), border=True)
        c3.metric("Ticket médio", brl(ticket), border=True)
        c4.metric("Comissões", brl(comissoes), border=True)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Vendedores", len(vendedores), border=True)
        c2.metric("Regiões", len(regioes), border=True)
        c3.metric("Clientes", len(clientes), border=True)
        c4.metric("Produtos", len(produtos), border=True)
        st.html(titulo_html("Vendas por região"))
        if regioes.empty or regioes["total_vendido"].sum() == 0:
            st.info("Ainda não há vendas.")
        else:
            grafico_barras(regioes, "regiao", "total_vendido", "Região", preencher=True)

    with lateral, painel("ultimos", "Últimos pedidos"):
        if pedidos.empty:
            st.info("Nenhum pedido cadastrado.")
        else:
            itens = "".join(
                f'<div class="item-pedido">'
                f'<div class="cliente">Nº {r.id_pedido} · {escape(str(r.cliente))}</div>'
                f'<div class="total">{brl(r.total_pedido)}</div>'
                f'<div class="detalhe">{data_hora(r.data_pedido)} · {escape(str(r.vendedor))}</div>'
                f'</div>'
                for r in pedidos.itertuples())
            st.html(f'<div class="lista-pedidos">{itens}</div>')


# =============================================================================
# Cadastros — tabela com busca à esquerda, formulário fixo à direita
# =============================================================================

def lista_com_busca(chave: str, titulo: str, df: pd.DataFrame, colunas: dict[str, str], **formatos):
    """Painel esquerdo dos cadastros. Devolve a linha selecionada (Series) ou None."""
    with painel(f"lista_{chave}"):
        c1, c2 = st.columns([1, 1], vertical_alignment="center")
        # .marca-cadastros: faz o CSS sublinhar "Cadastros" na navbar nestas telas
        c1.html(titulo_html(titulo, f"{len(df)} registro(s) · clique numa linha para editar")
                + '<span class="marca-cadastros"></span>')
        termo = c2.text_input("Buscar", placeholder="Buscar...", label_visibility="collapsed",
                              key=f"busca_{chave}", icon=":material/search:")
        visivel = filtrar(df, termo).reset_index(drop=True)
        posicao = tabela(visivel, colunas, chave=f"tabela_{chave}_{versao_selecao(chave)}_{termo}",
                         **formatos)
    return None if posicao is None or posicao >= len(visivel) else visivel.iloc[posicao]


def cabecalho_edicao(chave: str, titulo: str, subtitulo: str | None = None) -> None:
    c1, c2 = st.columns([3, 1], vertical_alignment="center")
    c1.html(titulo_html(titulo, subtitulo))
    c2.button("Novo", icon=":material/add:", key=f"novo_{chave}", width="stretch",
              on_click=limpar_selecao, args=(chave,), help="Desmarcar a linha e cadastrar um novo")


def pagina_vendedores() -> None:
    df = carregar(db.listar_vendedores)
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
                    executar(db.cadastrar_vendedor, nome.strip(), comissao, opcional(telefone),
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
                executar(db.atualizar_vendedor, id_, nome.strip(), comissao,
                         opcional(telefone), opcional(email), sucesso="Vendedor atualizado.")
        form_excluir("vendedor", id_, db.excluir_vendedor, "Vendedor excluído.",
                     ao_sucesso=lambda: limpar_selecao("vendedores"))


def pagina_regioes() -> None:
    df = carregar(db.listar_regioes)
    vendedores = carregar(db.listar_vendedores)
    esquerda, direita = st.columns([3, 2])
    with esquerda:
        sel = lista_com_busca("regioes", "Regiões", df,
                              {"id_regiao": "Código", "nome": "Região", "descricao": "Descrição",
                               "vendedor": "Vendedor responsável", "qtd_clientes": "Clientes"})

    with direita, painel("form_regioes"):
        if vendedores.empty:
            st.info("Cadastre um vendedor antes de criar regiões.")
            return
        nome_vendedor = rotulo_por_id(vendedores, "id_vendedor", "nome")
        ids_vendedores = list(vendedores["id_vendedor"])

        if sel is None:
            st.html(titulo_html("Nova região", "Região fechada: cada região tem um único vendedor."))
            with st.form("regiao_incluir", clear_on_submit=True):
                nome = st.text_input("Nome da região *")
                vendedor = st.selectbox("Vendedor responsável *", ids_vendedores, format_func=nome_vendedor)
                descricao = st.text_area("Descrição (bairros, cidades...)", height=80)
                if st.form_submit_button("Cadastrar região", type="primary"):
                    executar(db.cadastrar_regiao, nome.strip(), int(vendedor), opcional(descricao),
                             sucesso="Região cadastrada (código {id}).")
            return

        id_ = int(sel["id_regiao"])
        cabecalho_edicao("regioes", f"Editar região {id_}", texto(sel["nome"]))
        with st.form(f"regiao_editar_{id_}"):
            nome = st.text_input("Nome da região *", texto(sel["nome"]))
            vendedor = st.selectbox("Vendedor responsável *", ids_vendedores, format_func=nome_vendedor,
                                    index=ids_vendedores.index(sel["id_vendedor"]))
            descricao = st.text_area("Descrição", texto(sel["descricao"]), height=80)
            st.caption("Trocar o vendedor vale para pedidos novos; "
                       "pedidos antigos continuam com quem fez a venda.")
            if st.form_submit_button("Salvar alterações", type="primary"):
                executar(db.atualizar_regiao, id_, nome.strip(), int(vendedor),
                         opcional(descricao), sucesso="Região atualizada.")
        form_excluir("região", id_, db.excluir_regiao, "Região excluída.",
                     ao_sucesso=lambda: limpar_selecao("regioes"))


def pagina_clientes() -> None:
    df = carregar(db.listar_clientes)
    regioes = carregar(db.listar_regioes)
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
                    executar(db.cadastrar_cliente, nome.strip(), so_digitos(cpf), int(regiao),
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
                executar(db.atualizar_cliente, id_, nome.strip(), so_digitos(cpf), int(regiao),
                         opcional(telefone), opcional(email), opcional(endereco),
                         sucesso="Cliente atualizado.")
        form_excluir("cliente", id_, db.excluir_cliente, "Cliente excluído.",
                     ao_sucesso=lambda: limpar_selecao("clientes"))


def pagina_produtos() -> None:
    df = carregar(db.listar_produtos)
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
                    executar(db.cadastrar_produto, descricao.strip(), preco, estoque,
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
                executar(db.atualizar_produto, id_, descricao.strip(), preco, estoque,
                         sucesso="Produto atualizado.")
        form_excluir("produto", id_, db.excluir_produto, "Produto excluído.",
                     ao_sucesso=lambda: limpar_selecao("produtos"))


def rotulo_por_id(df: pd.DataFrame, coluna_id: str, coluna_nome: str):
    nomes = dict(zip(df[coluna_id], df[coluna_nome]))
    return lambda i: f"{i} — {nomes.get(i, '')}"


# =============================================================================
# Pedidos — lista à esquerda, pedido selecionado (ou novo) à direita
# =============================================================================

def pagina_pedidos() -> None:
    pedidos = carregar(db.listar_pedidos)
    clientes = carregar(db.listar_clientes)
    produtos = carregar(db.listar_produtos)

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
            novo_pedido(clientes, produtos)
        else:
            detalhe_pedido(int(visivel.iloc[posicao]["id_pedido"]), pedidos, clientes, produtos)


def cabecalho_pedido(titulo: str, subtitulo: str | None = None):
    """Título à esquerda e TOTAL em destaque à direita. Devolve o espaço do total."""
    c1, c2 = st.columns([3, 2], vertical_alignment="center")
    c1.html(titulo_html(titulo, subtitulo))
    return c2.empty()


def total_destaque(lugar, valor, rotulo: str = "Total do pedido") -> None:
    lugar.html(f'<div class="total-destaque"><span>{escape(rotulo)}</span>'
               f'<strong>{brl(valor)}</strong></div>')


def novo_pedido(clientes: pd.DataFrame, produtos: pd.DataFrame) -> None:
    with painel("pedido"):
        espaco_total = cabecalho_pedido("Novo pedido", "O vendedor vem da região do cliente")
        with st.container(key="painel_pedido_corpo", height="stretch"):
            total = _corpo_novo_pedido(clientes, produtos)
        total_destaque(espaco_total, total)


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
    rotulos = {f"{i} — {prod.loc[i, 'descricao']}": i for i in prod.index}
    itens = st.data_editor(
        pd.DataFrame({"produto": pd.Series(dtype="object"), "quantidade": pd.Series(dtype="float"),
                      "preco_unitario": pd.Series(dtype="float"), "desconto": pd.Series(dtype="float")}),
        num_rows="dynamic", width="stretch", key=f"novo_itens_{versao}",
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
        if _vazio(r.produto) or r.produto not in rotulos:
            continue
        id_produto = rotulos[r.produto]
        quantidade = 0.0 if _vazio(r.quantidade) else float(r.quantidade)
        preco_informado = None if _vazio(r.preco_unitario) else float(r.preco_unitario)
        preco = float(prod.loc[id_produto, "preco"]) if preco_informado is None else preco_informado
        desconto = 0.0 if _vazio(r.desconto) else float(r.desconto)
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
            id_pedido = db.cadastrar_pedido_com_itens(int(id_cliente), int(c["id_vendedor"]),
                                                      percentual, momento, linhas)
        except db.ErroBanco as erro:
            st.error(str(erro), icon="🚫")
            return total
        st.session_state["_versao_novo_pedido"] = versao + 1
        st.session_state["_aviso"] = f"Pedido nº {id_pedido} cadastrado — total {brl(total)}."
        st.rerun()
    return total


def detalhe_pedido(sel: int, pedidos: pd.DataFrame, clientes: pd.DataFrame,
                   produtos: pd.DataFrame) -> None:
    ped = pedidos.set_index("id_pedido")
    p = ped.loc[sel]

    with painel("pedido"):
        espaco_total = cabecalho_pedido(f"Pedido nº {sel}", data_hora(p["data_pedido"]))
        total_destaque(espaco_total, p["total_pedido"])

        with st.container(key="painel_pedido_corpo", height="stretch"):
            st.html(
                '<div class="ficha">'
                f'<div><span>Cliente</span><b>{escape(str(p["cliente"]))}</b></div>'
                f'<div><span>Vendedor</span><b>{escape(str(p["vendedor"]))}</b></div>'
                f'<div><span>Região</span><b>{escape(str(p["regiao"]))}</b></div>'
                f'<div><span>Comissão</span><b>{pct(p["percentual_comissao"])} · '
                f'{brl(p["valor_comissao"])}</b></div>'
                '</div>')

            itens = carregar(db.listar_itens_pedido, int(sel))
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
                            executar(db.atualizar_item_pedido, int(sel), int(id_item), quantidade, preco,
                                     desconto, sucesso="Item atualizado.")
                        if remover:
                            executar(db.excluir_item_pedido, int(sel), int(id_item),
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
                                              f"(estoque {qtd(prod.loc[i, 'estoque'])})")
                    c1, c2, c3 = st.columns(3)
                    quantidade = c1.number_input("Quantidade", 0.001, None, 1.0, 1.0, "%.3f")
                    preco = c2.number_input("Preço unit. (R$)", 0.0, None, None, 10.0, "%.2f",
                                            placeholder="preço do produto")
                    desconto = c3.number_input("Desconto (%)", 0.0, 100.0, 0.0, 0.5, "%.2f")
                    if st.form_submit_button("Adicionar item", type="primary", disabled=not disponiveis):
                        executar(db.cadastrar_item_pedido, int(sel), int(id_produto), quantidade, preco,
                                 desconto, sucesso="Item adicionado ao pedido.")

            with aba_dados:
                cli = clientes.set_index("id_cliente")
                ids_clientes = list(cli.index)
                with st.form(f"pedido_editar_{sel}"):
                    id_cliente = st.selectbox(
                        "Cliente", ids_clientes, index=ids_clientes.index(p["id_cliente"]),
                        format_func=lambda i: f"{cli.loc[i, 'nome']} — {cli.loc[i, 'regiao']}")
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
                        executar(db.atualizar_pedido, int(sel), int(id_cliente), vendedor, percentual,
                                 momento, sucesso=f"Pedido nº {sel} atualizado.")

            with aba_excluir:
                form_excluir("pedido", sel, db.excluir_pedido, f"Pedido nº {sel} excluído.",
                             aviso="Os itens também são apagados e o estoque deles é devolvido.",
                             ao_sucesso=lambda: limpar_selecao("pedidos"))


# =============================================================================
# Relatórios — abas; em cada aba, gráfico de um lado e tabela do outro
# =============================================================================

def lado_a_lado(chave: str, proporcao=(1, 1)):
    """Gráfico e tabela lado a lado, cada um com scroll próprio dentro da aba."""
    c1, c2 = st.columns(list(proporcao), gap="medium")
    with c1:
        esquerda = st.container(key=f"painel_{chave}_grafico", height="stretch")
    with c2:
        direita = st.container(key=f"painel_{chave}_tabela", height="stretch")
    return esquerda, direita


def pagina_relatorios() -> None:
    with painel("relatorios"):
        abas = st.tabs(["Por região", "Por cliente", "Por vendedor", "Clientes de uma região",
                        "Por produto", "Comissão por vendedor"], height="stretch")

        with abas[0]:
            df = carregar(db.vendas_por_regiao)
            graf, tab = lado_a_lado("regiao")
            with graf:
                st.metric("Total geral", brl(df["total_vendido"].sum() if not df.empty else 0))
                grafico_barras(df, "regiao", "total_vendido", "Região")
            with tab:
                tabela(df, {"regiao": "Região", "vendedor_responsavel": "Vendedor responsável",
                            "qtd_pedidos": "Pedidos", "total_vendido": "Total vendido"},
                       moeda=("total_vendido",))

        with abas[1]:
            df = carregar(db.vendas_por_cliente)
            graf, tab = lado_a_lado("cliente")
            with graf:
                grafico_barras(df, "cliente", "total_vendido", "Cliente", "Total comprado (R$)")
            with tab:
                tabela(df, {"cliente": "Cliente", "qtd_pedidos": "Pedidos",
                            "total_vendido": "Total comprado", "regiao": "Região",
                            "cpf_cnpj": "CPF/CNPJ"},
                       moeda=("total_vendido",))

        with abas[2]:
            df = carregar(db.vendas_por_vendedor)
            graf, tab = lado_a_lado("vendedor")
            with graf:
                grafico_barras(df, "vendedor", "total_vendido", "Vendedor")
            with tab:
                tabela(df, {"vendedor": "Vendedor", "qtd_pedidos": "Pedidos",
                            "total_vendido": "Total vendido", "total_comissao": "Comissão total"},
                       moeda=("total_vendido", "total_comissao"))

        with abas[3]:
            relatorio_clientes_regiao()

        with abas[4]:
            df = carregar(db.vendas_por_produto)
            graf, tab = lado_a_lado("produto")
            with graf:
                grafico_barras(df, "produto", "total_vendido", "Produto")
            with tab:
                tabela(df, {"produto": "Produto", "qtd_pedidos": "Pedidos",
                            "quantidade_vendida": "Qtd vendida", "total_vendido": "Total vendido"},
                       moeda=("total_vendido",), quantidade=("quantidade_vendida",))

        with abas[5]:
            relatorio_comissao()


def relatorio_clientes_regiao() -> None:
    regioes = carregar(db.listar_regioes)
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
    df = carregar(db.clientes_por_regiao, int(id_regiao))
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


def relatorio_comissao() -> None:
    vendedores = carregar(db.listar_vendedores)
    nomes = dict(zip(vendedores["id_vendedor"], vendedores["nome"]))
    graf, tab = lado_a_lado("comissao", proporcao=(2, 3))
    with graf:
        id_vendedor = st.selectbox("Vendedor", [None, *nomes],
                                   format_func=lambda i: "Todos os vendedores" if i is None else nomes[i])
        st.caption("Comissão calculada item a item com o percentual gravado em cada pedido. "
                   "“% efetivo” = comissão ÷ total vendido do produto.")
    df = carregar(db.comissao_por_vendedor, None if id_vendedor is None else int(id_vendedor))
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


# =============================================================================
# Navegação
# =============================================================================

st.html(PASTA_UI / "estilo.css")
st.logo(str(PASTA_UI / "logo.svg"), size="large")

paginas = st.navigation(
    {
        "": [
            st.Page(pagina_inicio, title="Início", icon=":material/home:", default=True),
            st.Page(pagina_pedidos, title="Pedidos", icon=":material/receipt_long:", url_path="pedidos"),
            st.Page(pagina_relatorios, title="Relatórios", icon=":material/bar_chart:",
                    url_path="relatorios"),
        ],
        "Cadastros": [
            st.Page(pagina_vendedores, title="Vendedores", icon=":material/badge:", url_path="vendedores"),
            st.Page(pagina_regioes, title="Regiões", icon=":material/map:", url_path="regioes"),
            st.Page(pagina_clientes, title="Clientes", icon=":material/groups:", url_path="clientes"),
            st.Page(pagina_produtos, title="Produtos", icon=":material/inventory_2:", url_path="produtos"),
        ],
    },
    position="top",
)

faixa_status()
mostrar_aviso()
paginas.run()

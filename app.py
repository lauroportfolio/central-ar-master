"""Central de Ar Ltda. — sistema de vendas (Streamlit + SQL Server).

Toda leitura e gravação passa por stored procedures (ver db.py).
"""

from __future__ import annotations

import re
from datetime import date, datetime

import altair as alt
import pandas as pd
import streamlit as st

import db

st.set_page_config(page_title="Central de Ar Ltda.", page_icon="❄️", layout="wide")

COR_BARRA = "#0B6FB8"


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


def executar(funcao, *args, sucesso: str, **kwargs) -> None:
    """Grava no banco. Erro (THROW do SQL Server) -> st.error com a mensagem do banco."""
    try:
        resultado = funcao(*args, **kwargs)
    except db.ErroBanco as erro:
        st.error(str(erro), icon="🚫")
        return
    st.session_state["_aviso"] = sucesso.format(id=resultado)
    st.rerun()


def mostrar_aviso() -> None:
    aviso = st.session_state.pop("_aviso", None)
    if aviso:
        st.success(aviso, icon="✅")


def tabela(df: pd.DataFrame, colunas: dict[str, str], moeda=(), percentual=(),
           quantidade=(), datas=(), altura="auto") -> None:
    """st.dataframe com cabeçalhos em português e valores formatados (R$, %, datas)."""
    if df.empty:
        st.info("Nenhum registro encontrado.")
        return
    visivel = df[list(colunas)].rename(columns=colunas)
    formatos = {}
    for grupo, funcao in ((moeda, brl), (percentual, pct), (quantidade, qtd), (datas, data_hora)):
        for coluna in grupo:
            formatos[colunas[coluna]] = funcao
    textos = [colunas[c] for c in colunas if c not in (*moeda, *percentual, *quantidade, *datas)
              and visivel[colunas[c]].dtype != "int64"]
    for coluna in textos:
        formatos.setdefault(coluna, texto)
    # Largura mínima para valores formatados não serem cortados ("R$ 2.84...")
    larguras = {}
    for grupo, px in ((moeda, 130), (datas, 135), (percentual, 105), (quantidade, 100)):
        for coluna in grupo:
            larguras[colunas[coluna]] = st.column_config.Column(width=px)
    st.dataframe(visivel.style.format(formatos), hide_index=True, width="stretch", height=altura,
                 column_config=larguras)


def grafico_barras(df: pd.DataFrame, categoria: str, valor: str, titulo_categoria: str,
                   titulo_valor: str = "Total vendido (R$)") -> None:
    """Barras horizontais (uma série só), ordenadas do maior para o menor, com tooltip em R$."""
    dados = df[[categoria, valor]].copy()
    dados = dados[dados[valor] > 0]
    if dados.empty:
        return
    dados["valor_formatado"] = dados[valor].map(brl)
    # Altura proporcional ao número de barras (36 px por categoria + eixo).
    # A altura é passada também ao st.altair_chart, senão o Streamlit encolhe o gráfico.
    altura = 36 * len(dados) + 60
    grafico = (
        alt.Chart(dados)
        .mark_bar(color=COR_BARRA, cornerRadiusEnd=4)
        .encode(
            y=alt.Y(f"{categoria}:N", sort="-x", title=None,
                    scale=alt.Scale(paddingInner=0.3, paddingOuter=0.15),
                    axis=alt.Axis(labelLimit=340, labelOverlap=False)),
            x=alt.X(f"{valor}:Q", title=titulo_valor, axis=alt.Axis(format="~s", grid=True)),
            tooltip=[alt.Tooltip(f"{categoria}:N", title=titulo_categoria),
                     alt.Tooltip("valor_formatado:N", title=titulo_valor.replace(" (R$)", ""))],
        )
        .properties(height=altura - 60)
        .configure_axis(gridOpacity=0.35, domain=False, tickColor="transparent")
        .configure_view(strokeWidth=0)
    )
    st.altair_chart(grafico, width="stretch", height=altura)


def rotulo_por_id(df: pd.DataFrame, coluna_id: str, coluna_nome: str):
    nomes = dict(zip(df[coluna_id], df[coluna_nome]))
    return lambda i: f"{i} — {nomes.get(i, '')}"


# =============================================================================
# Páginas
# =============================================================================

def pagina_inicio() -> None:
    st.title("❄️ Central de Ar Ltda.")
    st.caption("Setor de vendas — cadastros, pedidos e relatórios")
    mostrar_aviso()

    pedidos = carregar(db.listar_pedidos)
    vendedores = carregar(db.listar_vendedores)
    regioes = carregar(db.vendas_por_regiao)
    clientes = carregar(db.listar_clientes)
    produtos = carregar(db.listar_produtos)

    total = pedidos["total_pedido"].sum() if not pedidos.empty else 0
    comissoes = pedidos["valor_comissao"].sum() if not pedidos.empty else 0
    ticket = total / len(pedidos) if len(pedidos) else 0

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

    esquerda, direita = st.columns([1, 1], gap="large")
    with esquerda:
        st.subheader("Vendas por região")
        if regioes.empty or regioes["total_vendido"].sum() == 0:
            st.info("Ainda não há vendas.")
        else:
            grafico_barras(regioes, "regiao", "total_vendido", "Região")
    with direita:
        st.subheader("Últimos pedidos")
        tabela(pedidos.head(6), {"id_pedido": "Nº", "data_pedido": "Data", "cliente": "Cliente",
                                 "total_pedido": "Total"},
               moeda=("total_pedido",), datas=("data_pedido",))

    baixo = produtos[produtos["estoque"] < 10] if not produtos.empty else produtos
    if not baixo.empty:
        itens = ", ".join(f"{r.descricao} ({qtd(r.estoque)})" for r in baixo.itertuples())
        st.warning(f"Estoque baixo (menos de 10 unidades): {itens}", icon="⚠️")


# ----------------------------------------------------------------------------- Vendedores

def pagina_vendedores() -> None:
    st.title("Vendedores")
    mostrar_aviso()
    df = carregar(db.listar_vendedores)
    tabela(df, {"id_vendedor": "Código", "nome": "Nome", "telefone": "Telefone",
                "email": "E-mail", "comissao_fixa": "Comissão padrão"},
           percentual=("comissao_fixa",))

    aba_incluir, aba_editar = st.tabs(["➕ Incluir", "✏️ Editar / excluir"])

    with aba_incluir:
        with st.form("vendedor_incluir", clear_on_submit=True):
            c1, c2 = st.columns([3, 1])
            nome = c1.text_input("Nome *")
            comissao = c2.number_input("Comissão padrão (%) *", 0.0, 100.0, 5.0, 0.5, "%.2f")
            c1, c2 = st.columns(2)
            telefone = c1.text_input("Telefone")
            email = c2.text_input("E-mail")
            if st.form_submit_button("Cadastrar vendedor", type="primary"):
                executar(db.cadastrar_vendedor, nome.strip(), comissao, opcional(telefone),
                         opcional(email), sucesso="Vendedor cadastrado (código {id}).")

    with aba_editar:
        if df.empty:
            st.info("Cadastre um vendedor primeiro.")
            return
        sel = st.selectbox("Vendedor", df["id_vendedor"],
                           format_func=rotulo_por_id(df, "id_vendedor", "nome"))
        r = df.set_index("id_vendedor").loc[sel]
        with st.form(f"vendedor_editar_{sel}"):
            c1, c2 = st.columns([3, 1])
            nome = c1.text_input("Nome *", texto(r["nome"]))
            comissao = c2.number_input("Comissão padrão (%) *", 0.0, 100.0,
                                       float(r["comissao_fixa"]), 0.5, "%.2f")
            c1, c2 = st.columns(2)
            telefone = c1.text_input("Telefone", texto(r["telefone"]))
            email = c2.text_input("E-mail", texto(r["email"]))
            st.caption("Mudar a comissão padrão vale para pedidos novos; "
                       "pedidos já feitos guardam o próprio percentual.")
            if st.form_submit_button("Salvar alterações", type="primary"):
                executar(db.atualizar_vendedor, int(sel), nome.strip(), comissao,
                         opcional(telefone), opcional(email), sucesso="Vendedor atualizado.")
        form_excluir("vendedor", sel, db.excluir_vendedor, "Vendedor excluído.")


def form_excluir(entidade: str, id_, funcao, sucesso: str, aviso: str | None = None) -> None:
    with st.form(f"{entidade}_excluir_{id_}"):
        st.markdown(f"**Excluir {entidade}**")
        if aviso:
            st.caption(aviso)
        confirma = st.checkbox(f"Confirmo que quero excluir este {entidade}")
        if st.form_submit_button(f"Excluir {entidade}", icon="🗑️"):
            if not confirma:
                st.warning("Marque a confirmação para excluir.")
            else:
                executar(funcao, int(id_), sucesso=sucesso)


# ----------------------------------------------------------------------------- Regiões

def pagina_regioes() -> None:
    st.title("Regiões")
    st.caption("Região fechada: cada região é atendida por um único vendedor.")
    mostrar_aviso()
    df = carregar(db.listar_regioes)
    vendedores = carregar(db.listar_vendedores)
    tabela(df, {"id_regiao": "Código", "nome": "Região", "descricao": "Descrição",
                "vendedor": "Vendedor responsável", "qtd_clientes": "Clientes"})

    if vendedores.empty:
        st.info("Cadastre um vendedor antes de criar regiões.")
        return
    nome_vendedor = rotulo_por_id(vendedores, "id_vendedor", "nome")
    ids_vendedores = list(vendedores["id_vendedor"])

    aba_incluir, aba_editar = st.tabs(["➕ Incluir", "✏️ Editar / excluir"])

    with aba_incluir:
        with st.form("regiao_incluir", clear_on_submit=True):
            c1, c2 = st.columns(2)
            nome = c1.text_input("Nome da região *")
            vendedor = c2.selectbox("Vendedor responsável *", ids_vendedores, format_func=nome_vendedor)
            descricao = st.text_area("Descrição (bairros, cidades...)", height=80)
            if st.form_submit_button("Cadastrar região", type="primary"):
                executar(db.cadastrar_regiao, nome.strip(), int(vendedor), opcional(descricao),
                         sucesso="Região cadastrada (código {id}).")

    with aba_editar:
        if df.empty:
            st.info("Nenhuma região cadastrada.")
            return
        sel = st.selectbox("Região", df["id_regiao"], format_func=rotulo_por_id(df, "id_regiao", "nome"))
        r = df.set_index("id_regiao").loc[sel]
        with st.form(f"regiao_editar_{sel}"):
            c1, c2 = st.columns(2)
            nome = c1.text_input("Nome da região *", texto(r["nome"]))
            vendedor = c2.selectbox("Vendedor responsável *", ids_vendedores, format_func=nome_vendedor,
                                    index=ids_vendedores.index(r["id_vendedor"]))
            descricao = st.text_area("Descrição", texto(r["descricao"]), height=80)
            st.caption("Trocar o vendedor vale para pedidos novos; "
                       "pedidos antigos continuam com quem fez a venda.")
            if st.form_submit_button("Salvar alterações", type="primary"):
                executar(db.atualizar_regiao, int(sel), nome.strip(), int(vendedor),
                         opcional(descricao), sucesso="Região atualizada.")
        form_excluir("região", sel, db.excluir_regiao, "Região excluída.")


# ----------------------------------------------------------------------------- Clientes

def pagina_clientes() -> None:
    st.title("Clientes")
    mostrar_aviso()
    df = carregar(db.listar_clientes)
    regioes = carregar(db.listar_regioes)
    tabela(df, {"id_cliente": "Código", "nome": "Nome", "cpf_cnpj": "CPF/CNPJ",
                "telefone": "Telefone", "email": "E-mail", "endereco": "Endereço",
                "regiao": "Região", "vendedor": "Vendedor"})

    if regioes.empty:
        st.info("Cadastre uma região antes de cadastrar clientes.")
        return
    ids_regioes = list(regioes["id_regiao"])
    info_regiao = {r.id_regiao: f"{r.nome} (vendedor: {r.vendedor})" for r in regioes.itertuples()}

    aba_incluir, aba_editar = st.tabs(["➕ Incluir", "✏️ Editar / excluir"])

    with aba_incluir:
        with st.form("cliente_incluir", clear_on_submit=True):
            c1, c2 = st.columns([2, 1])
            nome = c1.text_input("Nome / razão social *")
            cpf = c2.text_input("CPF/CNPJ * (somente números)", max_chars=18)
            c1, c2 = st.columns(2)
            telefone = c1.text_input("Telefone")
            email = c2.text_input("E-mail")
            c1, c2 = st.columns([2, 1])
            endereco = c1.text_input("Endereço")
            regiao = c2.selectbox("Região *", ids_regioes, format_func=info_regiao.get)
            if st.form_submit_button("Cadastrar cliente", type="primary"):
                executar(db.cadastrar_cliente, nome.strip(), so_digitos(cpf), int(regiao),
                         opcional(telefone), opcional(email), opcional(endereco),
                         sucesso="Cliente cadastrado (código {id}).")

    with aba_editar:
        if df.empty:
            st.info("Nenhum cliente cadastrado.")
            return
        sel = st.selectbox("Cliente", df["id_cliente"], format_func=rotulo_por_id(df, "id_cliente", "nome"))
        r = df.set_index("id_cliente").loc[sel]
        with st.form(f"cliente_editar_{sel}"):
            c1, c2 = st.columns([2, 1])
            nome = c1.text_input("Nome / razão social *", texto(r["nome"]))
            cpf = c2.text_input("CPF/CNPJ * (somente números)", texto(r["cpf_cnpj"]), max_chars=18)
            c1, c2 = st.columns(2)
            telefone = c1.text_input("Telefone", texto(r["telefone"]))
            email = c2.text_input("E-mail", texto(r["email"]))
            c1, c2 = st.columns([2, 1])
            endereco = c1.text_input("Endereço", texto(r["endereco"]))
            regiao = c2.selectbox("Região *", ids_regioes, format_func=info_regiao.get,
                                  index=ids_regioes.index(r["id_regiao"]))
            if st.form_submit_button("Salvar alterações", type="primary"):
                executar(db.atualizar_cliente, int(sel), nome.strip(), so_digitos(cpf), int(regiao),
                         opcional(telefone), opcional(email), opcional(endereco),
                         sucesso="Cliente atualizado.")
        form_excluir("cliente", sel, db.excluir_cliente, "Cliente excluído.")


# ----------------------------------------------------------------------------- Produtos

def pagina_produtos() -> None:
    st.title("Produtos")
    mostrar_aviso()
    df = carregar(db.listar_produtos)
    tabela(df, {"id_produto": "Código", "descricao": "Descrição", "preco": "Preço",
                "estoque": "Estoque"}, moeda=("preco",), quantidade=("estoque",))

    aba_incluir, aba_editar = st.tabs(["➕ Incluir", "✏️ Editar / excluir"])

    with aba_incluir:
        with st.form("produto_incluir", clear_on_submit=True):
            descricao = st.text_input("Descrição *")
            c1, c2 = st.columns(2)
            preco = c1.number_input("Preço (R$) *", 0.0, None, 0.0, 10.0, "%.2f")
            estoque = c2.number_input("Estoque *", 0.0, None, 0.0, 1.0, "%.3f")
            if st.form_submit_button("Cadastrar produto", type="primary"):
                executar(db.cadastrar_produto, descricao.strip(), preco, estoque,
                         sucesso="Produto cadastrado (código {id}).")

    with aba_editar:
        if df.empty:
            st.info("Nenhum produto cadastrado.")
            return
        sel = st.selectbox("Produto", df["id_produto"],
                           format_func=rotulo_por_id(df, "id_produto", "descricao"))
        r = df.set_index("id_produto").loc[sel]
        with st.form(f"produto_editar_{sel}"):
            descricao = st.text_input("Descrição *", texto(r["descricao"]))
            c1, c2 = st.columns(2)
            preco = c1.number_input("Preço (R$) *", 0.0, None, float(r["preco"]), 10.0, "%.2f")
            estoque = c2.number_input("Estoque *", 0.0, None, float(r["estoque"]), 1.0, "%.3f")
            st.caption("O estoque baixa sozinho quando um item é vendido (trigger no banco). "
                       "Mudar o preço não altera pedidos já feitos.")
            if st.form_submit_button("Salvar alterações", type="primary"):
                executar(db.atualizar_produto, int(sel), descricao.strip(), preco, estoque,
                         sucesso="Produto atualizado.")
        form_excluir("produto", sel, db.excluir_produto, "Produto excluído.")


# ----------------------------------------------------------------------------- Pedidos

def pagina_pedidos() -> None:
    st.title("Pedidos")
    mostrar_aviso()
    pedidos = carregar(db.listar_pedidos)
    clientes = carregar(db.listar_clientes)
    produtos = carregar(db.listar_produtos)

    tabela(pedidos, {"id_pedido": "Nº", "data_pedido": "Data", "cliente": "Cliente",
                     "regiao": "Região", "vendedor": "Vendedor", "qtd_itens": "Itens",
                     "total_pedido": "Total", "percentual_comissao": "Comissão (%)",
                     "valor_comissao": "Comissão (R$)"},
           moeda=("total_pedido", "valor_comissao"), percentual=("percentual_comissao",),
           datas=("data_pedido",), altura=320)

    aba_novo, aba_detalhe = st.tabs(["🧾 Novo pedido", "🔍 Detalhes / editar"])
    with aba_novo:
        novo_pedido(clientes, produtos)
    with aba_detalhe:
        detalhe_pedido(pedidos, clientes, produtos)


def novo_pedido(clientes: pd.DataFrame, produtos: pd.DataFrame) -> None:
    if clientes.empty or produtos.empty:
        st.info("Cadastre pelo menos um cliente e um produto para lançar pedidos.")
        return

    versao = st.session_state.setdefault("_versao_novo_pedido", 0)
    cli = clientes.set_index("id_cliente")

    id_cliente = st.selectbox("Cliente *", list(cli.index), index=None,
                              placeholder="Escolha o cliente",
                              format_func=lambda i: f"{cli.loc[i, 'nome']} — {cli.loc[i, 'regiao']}",
                              key=f"novo_cliente_{versao}")
    if id_cliente is None:
        st.caption("O vendedor é preenchido automaticamente pela região do cliente.")
        return
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
    c1, c2, c3 = st.columns(3)
    c1.metric("Itens", len(linhas), border=True)
    c2.metric("Total do pedido", brl(total), border=True)
    c3.metric("Comissão do vendedor", brl(comissao), border=True)

    if linhas:
        resumo = pd.DataFrame(linhas)
        tabela(resumo, {"produto": "Produto", "quantidade": "Qtd", "preco": "Preço unit.",
                        "desconto": "Desconto", "valor": "Subtotal", "estoque": "Estoque atual"},
               moeda=("preco", "valor"), percentual=("desconto",), quantidade=("quantidade", "estoque"))

    if st.button("Salvar pedido", type="primary", icon="💾", disabled=not linhas):
        repetidos = {l["produto"] for l in linhas if sum(m["fk_produto"] == l["fk_produto"] for m in linhas) > 1}
        if repetidos:
            st.error(f"Produto repetido no pedido: {', '.join(repetidos)}. Junte numa linha só.", icon="🚫")
            return
        momento = datetime.combine(dia, datetime.now().time().replace(microsecond=0))
        try:
            id_pedido = db.cadastrar_pedido_com_itens(int(id_cliente), int(c["id_vendedor"]),
                                                      percentual, momento, linhas)
        except db.ErroBanco as erro:
            st.error(str(erro), icon="🚫")
            return
        st.session_state["_versao_novo_pedido"] = versao + 1
        st.session_state["_aviso"] = f"Pedido nº {id_pedido} cadastrado — total {brl(total)}."
        st.rerun()


def detalhe_pedido(pedidos: pd.DataFrame, clientes: pd.DataFrame, produtos: pd.DataFrame) -> None:
    if pedidos.empty:
        st.info("Nenhum pedido cadastrado.")
        return

    ped = pedidos.set_index("id_pedido")
    sel = st.selectbox(
        "Pedido", list(ped.index),
        format_func=lambda i: f"Nº {i} — {data_hora(ped.loc[i, 'data_pedido'])} — "
                              f"{ped.loc[i, 'cliente']} — {brl(ped.loc[i, 'total_pedido'])}")
    p = ped.loc[sel]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Cliente", p["cliente"], border=True)
    c2.metric("Vendedor", p["vendedor"], border=True)
    c3.metric("Total", brl(p["total_pedido"]), border=True)
    c4.metric(f"Comissão ({pct(p['percentual_comissao'])})", brl(p["valor_comissao"]), border=True)

    itens = carregar(db.listar_itens_pedido, int(sel))
    tabela(itens, {"produto": "Produto", "quantidade": "Qtd", "preco_unitario": "Preço unit.",
                   "desconto": "Desconto", "valor_total": "Subtotal"},
           moeda=("preco_unitario", "valor_total"), percentual=("desconto",), quantidade=("quantidade",))

    col_esq, col_dir = st.columns(2, gap="large")

    # --- Dados do pedido
    with col_esq:
        cli = clientes.set_index("id_cliente")
        ids_clientes = list(cli.index)
        with st.form(f"pedido_editar_{sel}"):
            st.markdown("**Dados do pedido**")
            id_cliente = st.selectbox("Cliente", ids_clientes,
                                      index=ids_clientes.index(p["id_cliente"]),
                                      format_func=lambda i: f"{cli.loc[i, 'nome']} — {cli.loc[i, 'regiao']}")
            c1, c2 = st.columns(2)
            percentual = c1.number_input("Comissão (%)", 0.0, 100.0, float(p["percentual_comissao"]),
                                         0.5, "%.2f")
            dia = c2.date_input("Data", pd.Timestamp(p["data_pedido"]).date(), format="DD/MM/YYYY")
            st.caption("Se trocar o cliente, o vendedor passa a ser o responsável pela região dele.")
            if st.form_submit_button("Salvar dados do pedido", type="primary"):
                vendedor = (int(p["id_vendedor"]) if id_cliente == p["id_cliente"]
                            else int(cli.loc[id_cliente, "id_vendedor"]))
                original = pd.Timestamp(p["data_pedido"]).to_pydatetime()
                momento = datetime.combine(dia, original.time())
                executar(db.atualizar_pedido, int(sel), int(id_cliente), vendedor, percentual, momento,
                         sucesso=f"Pedido nº {sel} atualizado.")

        form_excluir("pedido", sel, db.excluir_pedido, f"Pedido nº {sel} excluído.",
                     aviso="Os itens também são apagados e o estoque deles é devolvido.")

    # --- Itens
    with col_dir:
        prod = produtos.set_index("id_produto")
        no_pedido = set(itens["id_produto"]) if not itens.empty else set()
        disponiveis = [i for i in prod.index if i not in no_pedido]
        with st.form(f"item_incluir_{sel}", clear_on_submit=True):
            st.markdown("**Adicionar item**")
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
            if st.form_submit_button("Adicionar item", disabled=not disponiveis):
                executar(db.cadastrar_item_pedido, int(sel), int(id_produto), quantidade, preco, desconto,
                         sucesso="Item adicionado ao pedido.")

        if not itens.empty:
            it = itens.set_index("id_produto")
            ids_itens = list(it.index)
            st.markdown("**Alterar ou remover item**")
            id_item = st.selectbox("Item", ids_itens, format_func=lambda i: it.loc[i, "produto"],
                                   key=f"item_sel_{sel}")
            atual = it.loc[id_item]
            with st.form(f"item_editar_{sel}_{id_item}"):
                c1, c2, c3 = st.columns(3)
                quantidade = c1.number_input("Quantidade", 0.001, None, float(atual["quantidade"]),
                                             1.0, "%.3f")
                preco = c2.number_input("Preço unit. (R$)", 0.0, None, float(atual["preco_unitario"]),
                                        10.0, "%.2f")
                desconto = c3.number_input("Desconto (%)", 0.0, 100.0, float(atual["desconto"]),
                                           0.5, "%.2f")
                b1, b2 = st.columns(2)
                salvar = b1.form_submit_button("Salvar item", type="primary")
                remover = b2.form_submit_button("Remover item", icon="🗑️")
                if salvar:
                    executar(db.atualizar_item_pedido, int(sel), int(id_item), quantidade, preco, desconto,
                             sucesso="Item atualizado.")
                if remover:
                    executar(db.excluir_item_pedido, int(sel), int(id_item),
                             sucesso="Item removido (estoque devolvido).")


# ----------------------------------------------------------------------------- Relatórios

def pagina_relatorios() -> None:
    st.title("Relatórios")
    abas = st.tabs(["Por região", "Por cliente", "Por vendedor", "Clientes de uma região",
                    "Por produto", "Comissão por vendedor"])

    with abas[0]:
        df = carregar(db.vendas_por_regiao)
        st.metric("Total geral", brl(df["total_vendido"].sum() if not df.empty else 0))
        tabela(df, {"regiao": "Região", "vendedor_responsavel": "Vendedor responsável",
                    "qtd_pedidos": "Pedidos", "total_vendido": "Total vendido"},
               moeda=("total_vendido",))
        if not df.empty:
            grafico_barras(df, "regiao", "total_vendido", "Região")

    with abas[1]:
        df = carregar(db.vendas_por_cliente)
        tabela(df, {"cliente": "Cliente", "cpf_cnpj": "CPF/CNPJ", "regiao": "Região",
                    "qtd_pedidos": "Pedidos", "total_vendido": "Total comprado"},
               moeda=("total_vendido",))
        if not df.empty:
            grafico_barras(df, "cliente", "total_vendido", "Cliente", "Total comprado (R$)")

    with abas[2]:
        df = carregar(db.vendas_por_vendedor)
        tabela(df, {"vendedor": "Vendedor", "qtd_pedidos": "Pedidos", "total_vendido": "Total vendido",
                    "total_comissao": "Comissão total"},
               moeda=("total_vendido", "total_comissao"))
        if not df.empty:
            grafico_barras(df, "vendedor", "total_vendido", "Vendedor")

    with abas[3]:
        regioes = carregar(db.listar_regioes)
        if regioes.empty:
            st.info("Nenhuma região cadastrada.")
        else:
            reg = regioes.set_index("id_regiao")
            id_regiao = st.selectbox("Região *", list(reg.index), index=None,
                                     placeholder="Escolha a região",
                                     format_func=lambda i: f"{reg.loc[i, 'nome']} (vendedor: {reg.loc[i, 'vendedor']})")
            if id_regiao is None:
                st.info("Escolha uma região para ver os clientes.")
            else:
                df = carregar(db.clientes_por_regiao, int(id_regiao))
                c1, c2 = st.columns(2)
                c1.metric("Clientes", len(df))
                c2.metric("Total comprado", brl(df["total_vendido"].sum() if not df.empty else 0))
                tabela(df, {"cliente": "Cliente", "cpf_cnpj": "CPF/CNPJ", "telefone": "Telefone",
                            "email": "E-mail", "endereco": "Endereço", "qtd_pedidos": "Pedidos",
                            "total_vendido": "Total comprado"},
                       moeda=("total_vendido",))

    with abas[4]:
        df = carregar(db.vendas_por_produto)
        tabela(df, {"produto": "Produto", "qtd_pedidos": "Pedidos", "quantidade_vendida": "Qtd vendida",
                    "total_vendido": "Total vendido"},
               moeda=("total_vendido",), quantidade=("quantidade_vendida",))
        if not df.empty:
            grafico_barras(df, "produto", "total_vendido", "Produto")

    with abas[5]:
        relatorio_comissao()


def relatorio_comissao() -> None:
    vendedores = carregar(db.listar_vendedores)
    nomes = dict(zip(vendedores["id_vendedor"], vendedores["nome"]))
    id_vendedor = st.selectbox("Vendedor", [None, *nomes],
                               format_func=lambda i: "Todos os vendedores" if i is None else nomes[i])
    df = carregar(db.comissao_por_vendedor, None if id_vendedor is None else int(id_vendedor))
    st.caption("Comissão calculada item a item com o percentual gravado em cada pedido. "
               "“% efetivo” = comissão ÷ total vendido do produto (varia quando os pedidos "
               "tiveram percentuais diferentes).")
    if df.empty:
        st.info("Nenhuma venda para este filtro.")
        return

    if id_vendedor is None:
        por_vendedor = df.groupby("vendedor", as_index=False)["valor_comissao"].sum()
        grafico_barras(por_vendedor, "vendedor", "valor_comissao", "Vendedor", "Comissão (R$)")

    for (_, nome), grupo in df.groupby(["id_vendedor", "vendedor"], sort=False):
        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 1, 1])
            c1.subheader(nome)
            c2.metric("Total vendido", brl(grupo["total_vendido"].sum()))
            c3.metric("Comissão", brl(grupo["valor_comissao"].sum()))
            tabela(grupo, {"produto": "Produto", "qtd_pedidos": "Pedidos",
                           "quantidade_vendida": "Qtd vendida", "total_vendido": "Total vendido",
                           "percentual_efetivo": "% efetivo", "valor_comissao": "Comissão"},
                   moeda=("total_vendido", "valor_comissao"), percentual=("percentual_efetivo",),
                   quantidade=("quantidade_vendida",))
            if id_vendedor is not None:
                grafico_barras(grupo, "produto", "valor_comissao", "Produto", "Comissão (R$)")


# =============================================================================
# Menu
# =============================================================================

PAGINAS = {
    "🏠 Início": pagina_inicio,
    "🧑‍💼 Vendedores": pagina_vendedores,
    "🗺️ Regiões": pagina_regioes,
    "👥 Clientes": pagina_clientes,
    "📦 Produtos": pagina_produtos,
    "🧾 Pedidos": pagina_pedidos,
    "📊 Relatórios": pagina_relatorios,
}

with st.sidebar:
    st.markdown("### ❄️ Central de Ar Ltda.")
    escolha = st.radio("Menu", list(PAGINAS), label_visibility="collapsed", key="menu")
    st.divider()
    st.caption(f"Banco: **{db.nome_banco()}** · modo **{db.modo_conexao()}**")

PAGINAS[escolha]()

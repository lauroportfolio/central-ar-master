"""Central de Ar Ltda. — sistema de vendas (Streamlit + SQL Server).

Ponto de entrada (streamlit run app.py). Aqui ficam só a configuração da página,
o CSS, a navbar, o idioma, a faixa de status e o roteamento para as telas em paginas/.

Camadas (ver README, "Estrutura do código"):
  paginas/      telas            -> usam componentes/ e dados/
  componentes/  peças de tela    -> não acessam o banco
  dados/        stored procedures (único lugar que fala com o SQL Server)
  util/         formatação, idioma (i18n) e o erro de banco compartilhado
"""

from pathlib import Path

import streamlit as st

import config
from componentes.acoes import mostrar_aviso
from componentes.dicas import OBSERVADOR_CORTE, ajuda
from componentes.janela import medir_janela
from componentes.idioma import inicializar_idioma, seletor_idioma
from componentes.status import faixa_sem_conexao, faixa_status
from componentes.tema import marcar_tema
from dados import pedidos as dados_pedidos
from dados import produtos as dados_produtos
from dados import vendedores as dados_vendedores
from paginas import inicio, pedidos, relatorios
from paginas.cadastros import clientes, produtos, regioes, vendedores
from util.erros import ErroBanco
from util.i18n import t

PASTA_UI = Path(__file__).parent / "ui"

inicializar_idioma()
st.set_page_config(page_title=t("app.titulo"), page_icon="❄️", layout="wide")
st.html(PASTA_UI / "estilo.css")
st.logo(str(PASTA_UI / "logo.svg"), size="large")

PAGINAS = {
    "": [
        st.Page(inicio.render, title=t("nav.inicio"), icon=":material/home:", url_path="inicio",
                default=True, help=ajuda("tooltips.nav.inicio")),
        st.Page(pedidos.render, title=t("nav.pedidos"), icon=":material/receipt_long:", url_path="pedidos",
                help=ajuda("tooltips.nav.pedidos")),
        st.Page(relatorios.render, title=t("nav.relatorios"), icon=":material/bar_chart:",
                url_path="relatorios", help=ajuda("tooltips.nav.relatorios")),
    ],
    t("nav.cadastros"): [
        st.Page(vendedores.render, title=t("nav.vendedores"), icon=":material/badge:", url_path="vendedores",
                help=ajuda("tooltips.nav.vendedores")),
        st.Page(regioes.render, title=t("nav.regioes"), icon=":material/map:", url_path="regioes",
                help=ajuda("tooltips.nav.regioes")),
        st.Page(clientes.render, title=t("nav.clientes"), icon=":material/groups:", url_path="clientes",
                help=ajuda("tooltips.nav.clientes")),
        st.Page(produtos.render, title=t("nav.produtos"), icon=":material/inventory_2:", url_path="produtos",
                help=ajuda("tooltips.nav.produtos")),
    ],
}
navegacao = st.navigation(PAGINAS, position="top")

# Scripts do navegador, num container fora da tela:
# - tema: os caminhos das páginas (o tema escolhido no menu ⋮ vale para todas, inclusive após F5);
# - textos cortados com "…": o tooltip com o texto completo só aparece quando está cortado;
# - largura da janela: as tabelas dividem o espaço das colunas conforme a tela.
with st.container(key="infra"):
    marcar_tema(["/"] + [f"/{p.url_path}" for paginas in PAGINAS.values() for p in paginas])
    st.html(OBSERVADOR_CORTE, unsafe_allow_javascript=True)
    medir_janela()
seletor_idioma(ajuda=ajuda("tooltips.idioma"))

try:
    faixa_status(dados_pedidos.listar(), dados_vendedores.listar(), dados_produtos.listar(),
                 banco=config.nome_banco(), modo=config.modo_conexao())
except ErroBanco:
    faixa_sem_conexao()

mostrar_aviso()
navegacao.run()

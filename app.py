"""Central de Ar Ltda. — sistema de vendas (Streamlit + SQL Server).

Ponto de entrada (streamlit run app.py). Aqui ficam só a configuração da página,
o CSS, a navbar, a faixa de status e o roteamento para as telas em paginas/.

Camadas (ver README, "Estrutura do código"):
  paginas/      telas            -> usam componentes/ e dados/
  componentes/  peças de tela    -> não acessam o banco
  dados/        stored procedures (único lugar que fala com o SQL Server)
  util/         formatação e o erro de banco compartilhado
"""

from pathlib import Path

import streamlit as st

import config
from componentes.acoes import mostrar_aviso
from componentes.status import faixa_sem_conexao, faixa_status
from dados import pedidos as dados_pedidos
from dados import produtos as dados_produtos
from dados import vendedores as dados_vendedores
from paginas import inicio, pedidos, relatorios
from paginas.cadastros import clientes, produtos, regioes, vendedores
from util.erros import ErroBanco

PASTA_UI = Path(__file__).parent / "ui"

st.set_page_config(page_title="Central de Ar Ltda.", page_icon="❄️", layout="wide")
st.html(PASTA_UI / "estilo.css")
st.logo(str(PASTA_UI / "logo.svg"), size="large")

navegacao = st.navigation(
    {
        "": [
            st.Page(inicio.render, title="Início", icon=":material/home:", url_path="inicio",
                    default=True),
            st.Page(pedidos.render, title="Pedidos", icon=":material/receipt_long:", url_path="pedidos"),
            st.Page(relatorios.render, title="Relatórios", icon=":material/bar_chart:",
                    url_path="relatorios"),
        ],
        "Cadastros": [
            st.Page(vendedores.render, title="Vendedores", icon=":material/badge:", url_path="vendedores"),
            st.Page(regioes.render, title="Regiões", icon=":material/map:", url_path="regioes"),
            st.Page(clientes.render, title="Clientes", icon=":material/groups:", url_path="clientes"),
            st.Page(produtos.render, title="Produtos", icon=":material/inventory_2:", url_path="produtos"),
        ],
    },
    position="top",
)

try:
    faixa_status(dados_pedidos.listar(), dados_vendedores.listar(), dados_produtos.listar(),
                 banco=config.nome_banco(), modo=config.modo_conexao())
except ErroBanco:
    faixa_sem_conexao()

mostrar_aviso()
navegacao.run()

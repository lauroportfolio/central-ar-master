"""Tooltips do app — uma API só, com o texto sempre vindo do idioma (chaves "tooltips.*").

Dois mecanismos com o MESMO visual (estilo do tooltip do shadcn/ui, em ui/estilo.css):
  ajuda("tooltips.x")              -> texto para o help= nativo dos widgets do Streamlit
                                       (st.metric, botões, campos, st.Page, cabeçalhos de coluna)
  com_dica(html, "tooltips.x")     -> envolve um elemento HTML nosso (faixa de status, cards...)
                                       com um tooltip em CSS puro: role="tooltip", aria-describedby,
                                       e abre também com o foco do teclado (Tab).
  icone_dica("tooltips.x")         -> ícone "ⓘ" + rótulo curto com tooltip (ex.: abas dos relatórios)
"""

from __future__ import annotations

import hashlib
from html import escape

from util.i18n import t


def ajuda(chave: str, **parametros) -> str:
    """Texto do tooltip para o parâmetro help= de um widget do Streamlit."""
    return t(chave, **parametros)


def com_dica(conteudo_html: str, chave: str, posicao: str = "baixo", alinhamento: str = "centro",
             bloco: bool = False, **parametros) -> str:
    """Envolve `conteudo_html` com um tooltip acessível.
    posicao: "baixo" | "cima";  alinhamento: "centro" | "inicio" | "fim";
    bloco=True: o elemento inteiro (largura total) abre o tooltip, ex.: um card."""
    texto = t(chave, **parametros)
    ident = "dica-" + hashlib.md5(f"{chave}|{texto}|{conteudo_html}".encode()).hexdigest()[:10]
    classes = f"com-dica dica-{posicao} dica-{alinhamento}" + (" bloco" if bloco else "")
    return (f'<span class="{classes}" tabindex="0" aria-describedby="{ident}">'
            f'{conteudo_html}<span class="dica" role="tooltip" id="{ident}">{escape(texto)}</span></span>')


def icone_dica(chave: str, rotulo_chave: str = "tooltips.relatorios.sobre", **parametros) -> str:
    """Ícone de informação com rótulo curto; o tooltip explica o conteúdo (ex.: uma aba de relatório)."""
    rotulo = f'<span class="icone-dica" aria-hidden="true">ⓘ</span> {escape(t(rotulo_chave))}'
    return f'<div class="linha-dica">{com_dica(rotulo, chave, alinhamento="inicio", **parametros)}</div>'

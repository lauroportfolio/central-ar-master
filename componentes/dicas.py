"""Tooltips do app — uma API só, com o texto sempre vindo do idioma (chaves "tooltips.*").

Dois mecanismos com o MESMO visual (estilo do tooltip do shadcn/ui, em ui/estilo.css):
  ajuda("tooltips.x")              -> texto para o help= nativo dos widgets do Streamlit
                                       (st.metric, botões, campos, st.Page, cabeçalhos de coluna)
  com_dica(html, "tooltips.x")     -> envolve um elemento HTML nosso (faixa de status, cards...)
                                       com um tooltip em CSS puro: role="tooltip", aria-describedby,
                                       e abre também com o foco do teclado (Tab).
  icone_dica("tooltips.x")         -> ícone "ⓘ" + rótulo curto com tooltip (ex.: abas dos relatórios)
  texto_cortado("Nome longo...")   -> texto de UMA linha com "…" quando não cabe; o tooltip
                                       (o texto completo, dado do banco, sem i18n) só aparece se o
                                       texto estiver cortado de verdade (ver OBSERVADOR_CORTE)
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


def texto_cortado(texto: str, conteudo_html: str | None = None, classe: str = "") -> str:
    """Uma linha com reticências; o tooltip mostra `texto` inteiro só quando está cortado.
    `conteudo_html`: o que aparece na tela, se for diferente do texto puro (ex.: com <b>).
    O balão é o ::after do elemento (mesmo visual do .dica), com o texto do atributo
    data-texto: assim o texto não fica duplicado no DOM (o leitor de tela já lê o texto
    inteiro, porque o "…" é só visual). Quem liga o balão e o foco pelo teclado (tabindex)
    é o OBSERVADOR_CORTE, que marca data-cortado quando o texto não cabe."""
    visivel = conteudo_html if conteudo_html is not None else escape(texto)
    return (f'<span class="corte {classe}" data-texto="{escape(texto, quote=True)}">'
            f'<span class="corte-texto">{visivel}</span></span>')


# Observador (instalado uma vez pelo app.py): marca data-cortado nos textos que não cabem
# (scrollWidth > clientWidth) e recalcula quando o tamanho muda (janela, painel, aba que
# aparece, fonte que termina de carregar) ou quando o Streamlit troca o conteúdo da tela.
# Atenção: nada de comentários "//" dentro do script (o Streamlit junta as linhas).
# i18n: ignorar (é código JavaScript, não texto de tela)
OBSERVADOR_CORTE = """<script>
(() => {
  if (window.__centralArCorte) return;
  let pendente = false;
  const tamanho = new ResizeObserver(() => agendar());
  const medir = () => {
    pendente = false;
    for (const el of document.querySelectorAll('.corte')) {
      const texto = el.querySelector(':scope > .corte-texto');
      if (!texto) continue;
      tamanho.observe(texto);
      const cortado = texto.scrollWidth > texto.clientWidth + 1;
      if (cortado === el.hasAttribute('data-cortado')) continue;
      if (cortado) {
        el.setAttribute('data-cortado', '');
        el.setAttribute('tabindex', '0');
      } else {
        el.removeAttribute('data-cortado');
        el.removeAttribute('tabindex');
      }
    }
  };
  const agendar = () => {
    if (pendente) return;
    pendente = true;
    requestAnimationFrame(medir);
  };
  window.__centralArCorte = new MutationObserver(agendar);
  window.__centralArCorte.observe(document.body, { childList: true, subtree: true, characterData: true });
  window.addEventListener('resize', agendar);
  if (document.fonts) document.fonts.ready.then(agendar);
  agendar();
})();
</script>"""

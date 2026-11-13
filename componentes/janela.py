"""Largura da janela do navegador, para as tabelas calcularem o espaço das colunas.

O Streamlit não informa ao Python o tamanho da tela (st.context não tem isso). Este
componente (st.components.v2, a API oficial de JavaScript -> Python) mede a janela no
navegador e devolve a largura arredondada para baixo em degraus de 32 px: assim
redimensionar a janela só roda o script de novo quando muda de degrau.

Antes da primeira medida (o 1º carregamento de cada sessão) vale a menor resolução
suportada (1280 px), em que nenhuma tabela tem scroll horizontal.
"""

from __future__ import annotations

import streamlit as st

LARGURA_BASE = 1280      # resolução em que as constantes ESPACO_* de componentes/tabela.py foram medidas
MARGEM_PAGINA = 32       # padding lateral da página (16 + 16)
DEGRAU = 32

# i18n: ignorar (é código JavaScript, não texto de tela)
_JS = """
export default function (componente) {
  const { setStateValue, data } = componente;
  const medir = () => Math.floor(window.innerWidth / data.degrau) * data.degrau;
  const enviar = () => {
    const largura = medir();
    if (largura !== window.__centralArLarguraEnviada) {
      window.__centralArLarguraEnviada = largura;
      setStateValue('largura', largura);
    }
  };
  window.__centralArLarguraEnviada = data.atual;
  let espera;
  const aoRedimensionar = () => {
    clearTimeout(espera);
    espera = setTimeout(enviar, 250);
  };
  window.addEventListener('resize', aoRedimensionar);
  enviar();
  return () => {
    clearTimeout(espera);
    window.removeEventListener('resize', aoRedimensionar);
  };
}
"""

_componente = st.components.v2.component("central_ar_largura_janela", js=_JS)


def medir_janela() -> None:
    """Monta o medidor (uma vez por execução, no container "infra" do app.py)."""
    atual = st.session_state.get("_largura_janela")
    resultado = _componente(key="largura_janela", data={"degrau": DEGRAU, "atual": atual},
                            on_largura_change=lambda: None)
    largura = getattr(resultado, "largura", None)
    if largura:
        st.session_state["_largura_janela"] = int(largura)
    # a largura que esta execução usou (os testes E2E esperam ela bater com a da janela)
    st.html(f'<span id="largura-janela" data-largura="{largura_janela()}">{largura_janela()}</span>')


def largura_janela() -> int:
    return st.session_state.get("_largura_janela") or LARGURA_BASE


def escala() -> float:
    """Quanto o espaço dos painéis cresce em relação a 1280 px (os painéis são frações da
    largura útil da página, então o espaço cresce na mesma proporção)."""
    return max(0.75, (largura_janela() - MARGEM_PAGINA) / (LARGURA_BASE - MARGEM_PAGINA))

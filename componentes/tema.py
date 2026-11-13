"""Marca o tema ativo (claro/escuro) para o CSS do app.

Por que um script: o Streamlit troca o tema pelo menu ⋮ só no navegador, sem rodar o
script Python de novo (st.context.theme não muda até o próximo rerun). Então quem
acompanha a troca é este observador: ele lê a cor de fundo que o Streamlit aplicou e
marca <html data-tema="claro|escuro">; o ui/estilo.css troca as variáveis de cor
a partir desse atributo. O container "infra" (app.py) é escondido pelo CSS (não ocupa espaço).
"""

import json

import streamlit as st

# Atenção: nada de comentários "//" dentro do script — o Streamlit junta as linhas do HTML
# e um comentário de linha engoliria o resto do código (sem erro nenhum no console).
#
# O que o script faz (instalado uma vez só):
# 1) marca <html data-tema> lendo o fundo do stApp, e de novo sempre que o Streamlit
#    injeta os estilos do outro tema no <head>;
# 2) o Streamlit guarda a escolha do menu ⋮ por CAMINHO de página
#    ("stActiveTheme-/clientes-v2"); um F5 em outra página voltaria ao padrão. Quando o
#    usuário escolhe um tema, o script replica a escolha para as chaves de todas as páginas.
#    (As gravações que o Streamlit faz ao carregar a página acontecem antes de o script
#    existir, então não sobrescrevem a escolha.)
# i18n: ignorar (é código JavaScript, não texto de tela)
_SCRIPT = """<script>
(() => {
  if (window.__centralArTema) return;
  const caminhos = __CAMINHOS__;
  const prefixo = 'stActiveTheme-';
  const gravar = Storage.prototype.setItem;
  Storage.prototype.setItem = function (chave, valor) {
    gravar.call(this, chave, valor);
    if (this === window.localStorage && String(chave).startsWith(prefixo) && !window.__centralArSincronizando) {
      window.__centralArSincronizando = true;
      try {
        for (const c of caminhos) {
          const outra = prefixo + c + '-v2';
          if (outra !== chave) gravar.call(this, outra, valor);
        }
      } finally { window.__centralArSincronizando = false; }
    }
  };
  const marcar = () => {
    const app = document.querySelector('[data-testid="stApp"]');
    if (!app) return;
    const rgb = (getComputedStyle(app).backgroundColor.match(/\\d+/g) || [255, 255, 255]).map(Number);
    const luminancia = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2];
    const tema = luminancia < 128 ? 'escuro' : 'claro';
    if (document.documentElement.dataset.tema !== tema) document.documentElement.dataset.tema = tema;
  };
  marcar();
  window.__centralArTema = new MutationObserver(marcar);
  window.__centralArTema.observe(document.head, { childList: true, subtree: true, characterData: true });
  window.__centralArTema.observe(document.body, { attributes: true, subtree: true, attributeFilter: ['class'] });
})();
</script>"""


def marcar_tema(caminhos: list[str]) -> None:
    """Instala o marcador de tema. `caminhos`: URLs das páginas (ex.: ["/", "/pedidos"]).
    Chame dentro do container "infra" (app.py), que fica fora da tela."""
    st.html(_SCRIPT.replace("__CAMINHOS__", json.dumps(caminhos)), unsafe_allow_javascript=True)

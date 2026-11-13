"""Tabela formatada (R$, %, datas), busca e seleção de linha."""

from __future__ import annotations

import hashlib

import pandas as pd
import streamlit as st

from componentes.janela import escala
from util.formatacao import brl, data_curta, data_hora, pct, qtd, texto
from util.i18n import t


# ----------------------------------------------------------------------------- larguras
# O grid (glide-data-grid) desenha as células num canvas. Para nenhuma tabela ter scroll
# horizontal, TODA coluna recebe largura fixa calculada para caber no espaço da tabela.
# Esse espaço é medido em 1280x720 (constantes abaixo) e cresce na proporção da janela
# (componentes/janela.py); se sobrar algum pixel, o próprio grid estica as colunas até a
# borda (width="stretch").
#
# Espaço útil (px) de cada lugar com tabela, medido em 1280x720 (com folga de ~10 px):
ESPACO_CADASTRO = 700        # lista dos cadastros (3/5 da tela)
ESPACO_LISTA_PEDIDOS = 452   # lista de pedidos (2/5 da tela)
ESPACO_PEDIDO = 700          # itens do pedido / resumo do pedido novo (3/5 da tela)
ESPACO_RELATORIO = 584       # aba de relatório, tabela ao lado do gráfico (1/2)
ESPACO_RELATORIO_LARGO = 640 # aba de relatório com a tabela em 3/5 (comissão, clientes de uma região)

PX_FOLGA = 20                # padding da célula (8 + 8) + sobra
PX_FOLGA_CABECALHO = 28      # o cabeçalho mostra também o ícone de ordenação
PX_AJUDA = 16                # ícone de ajuda (help) no cabeçalho
PX_SELECAO = 34              # coluna das caixinhas de seleção
PX_TEXTO_MIN = 64            # nenhuma coluna de texto fica mais estreita que isto
# A barra de rolagem vertical do grid é desenhada POR CIMA do canvas, sobre a última
# coluna. Um espaço de 1 em (~14 px) no fim do valor da última coluna mantém o texto
# fora da barra (vale em qualquer navegador, com barra fina, larga ou sobreposta).
RESERVA_BARRA = "\u2003"
PX_RESERVA = 14
RETICENCIAS = "…"
# Colunas de texto que são códigos (nunca cortadas: largura do maior valor)
TEXTO_FIXO = {"cpf_cnpj", "telefone"}
VAZIO = "—"                  # o que aparece no lugar de um valor nulo (o padrão seria "None")


# Largura (px) de cada caractere na fonte do grid (Source Sans, 12,25 px = tamanho "sm"
# do tema), medida no Chromium com canvas.measureText. Caractere fora da tabela: 8 px.
_LARGURAS = {
    2: " ",  # i18n: ignorar (larguras de caracteres)
    3: "!'.:Ifijl{|Ííª·",  # i18n: ignorar (larguras de caracteres)
    4: "(),-/;[\\]rt}º°",  # i18n: ignorar (larguras de caracteres)
    5: '"*sx',  # i18n: ignorar (larguras de caracteres)
    6: "0123456789#$=?EFJLPRSVXY^_cegkovyz~ÈÉÊçèéêóôõ–",  # i18n: ignorar (larguras de caracteres)
    7: "+<>ABCKTZ`abdhnpquÀÁÂÃÄÇàáâãäúüñ",  # i18n: ignorar (larguras de caracteres)
    8: "&DGHNUÚÜÑ",  # i18n: ignorar (larguras de caracteres)
    9: "MOQwÓÔÕ",  # i18n: ignorar (larguras de caracteres)
    10: "%W—",  # i18n: ignorar (larguras de caracteres)
    11: "@m…",  # i18n: ignorar (larguras de caracteres)
}
_PX_CARACTERE = {ch: px for px, caracteres in _LARGURAS.items() for ch in caracteres}


def largura_texto(texto: str) -> int:
    """Largura (px) aproximada do texto desenhado no grid."""
    return sum(_PX_CARACTERE.get(ch, 8) for ch in texto)


def cortar(valor: str, largura_px: int) -> str:
    """Corta o texto com "…" se ele não cabe numa célula de `largura_px`."""
    cabe = largura_px - PX_FOLGA
    if largura_texto(valor) <= cabe:
        return valor
    cabe -= largura_texto(RETICENCIAS)
    usado, fim = 0, 0
    for fim, ch in enumerate(valor):
        usado += _PX_CARACTERE.get(ch, 8)
        if usado > cabe:
            break
    return valor[:fim].rstrip() + RETICENCIAS


def _repartir(naturais: dict[str, int], minimos: dict[str, int], espaco: int) -> dict[str, int]:
    """Divide `espaco` entre as colunas de texto: quem precisa de menos que a parte igual
    fica com o que precisa; o resto é dividido igualmente entre as colunas mais longas."""
    larguras, pendentes = {}, dict(naturais)
    while pendentes:
        parte = max(0, espaco - sum(larguras.values())) // len(pendentes)
        cabem = {c: px for c, px in pendentes.items() if px <= parte}
        if not cabem:
            for c in pendentes:
                larguras[c] = max(parte, minimos[c])
            break
        larguras.update(cabem)
        for c in cabem:
            del pendentes[c]
    return larguras


def larguras_editor(colunas: dict[str, str], flexivel: str, espaco: int,
                    ajudas=(), minimo_numerico: int = 90) -> dict[str, int]:
    """Larguras (px) das colunas de um st.data_editor com linhas dinâmicas: as numéricas
    ficam com a largura do cabeçalho (ou `minimo_numerico`) e a coluna `flexivel` (o texto)
    fica com o resto do espaço, sem scroll horizontal."""
    espaco = int(espaco * escala())
    px = {c: max(minimo_numerico, largura_texto(rotulo) + PX_FOLGA_CABECALHO + (PX_AJUDA if c in ajudas else 0))
          for c, rotulo in colunas.items() if c != flexivel}
    px[flexivel] = max(PX_TEXTO_MIN, espaco - PX_SELECAO - PX_RESERVA - sum(px.values()))
    return px


def tabela(df: pd.DataFrame, colunas: dict[str, str], moeda=(), percentual=(),
           quantidade=(), datas=(), datas_curtas=(), altura="stretch", chave: str | None = None,
           larguras: dict[str, int] | None = None, ao_selecionar=None, selecao_padrao=None,
           ajudas: dict[str, str] | None = None, espaco: int = ESPACO_RELATORIO):
    """st.dataframe com cabeçalhos traduzidos e valores formatados (R$, %, datas).
    Com `chave`, permite selecionar uma linha e devolve a posição dela (ou None).
    `espaco`: largura útil (px) do lugar da tabela em 1280x720 (constantes ESPACO_*);
      as colunas de texto dividem o que sobra e textos longos ganham "…".
    `larguras` fixa a largura (px) de colunas específicas, ex.: {"produto": 180}.
    `ajudas` põe um tooltip no cabeçalho de colunas, ex.: {"total_pedido": "..."}."""
    if df.empty:
        st.info(t("comum.nenhum_registro"))
        return None
    ajudas, larguras = ajudas or {}, larguras or {}
    espaco = int(espaco * escala())
    formatadores = {}
    for grupo, funcao in ((moeda, brl), (percentual, pct), (quantidade, qtd), (datas, data_hora),
                          (datas_curtas, data_curta)):
        for coluna in grupo:
            formatadores[coluna] = funcao
    numericas = set(formatadores) | {c for c in colunas if df[c].dtype == "int64"}
    textos = [c for c in colunas if c not in numericas]
    for coluna in colunas:
        formatadores.setdefault(coluna, texto if coluna in textos else str)
    ultima = list(colunas)[-1]

    # A largura de cada coluna sai do maior valor formatado e do cabeçalho
    def cabecalho(c: str) -> int:
        return largura_texto(colunas[c]) + PX_FOLGA_CABECALHO + (PX_AJUDA if c in ajudas else 0)

    def natural(c: str) -> int:
        maior = max((largura_texto(formatadores[c](v)) for v in df[c]), default=0)
        return max(cabecalho(c), maior + PX_FOLGA)

    px = {c: larguras.get(c) or natural(c) for c in colunas
          if c in numericas or c in larguras or c in TEXTO_FIXO}
    livres = [c for c in textos if c not in px]
    if livres:
        sobra = espaco - (PX_SELECAO if chave else 0) - sum(px.values())
        sobra -= PX_RESERVA if ultima not in livres else 0
        naturais = {c: natural(c) + (PX_RESERVA if c == ultima else 0) for c in livres}
        minimos = {c: max(PX_TEXTO_MIN, cabecalho(c)) for c in livres}
        px.update(_repartir(naturais, minimos, sobra))
    if ultima not in livres:
        px[ultima] += PX_RESERVA

    def exibir(c: str):
        """Formata o valor; texto longo ganha "…" (o texto completo continua no DOM de
        acessibilidade do grid e aparece no formulário ao clicar na linha); o valor da
        última coluna ganha o espaço reservado para a barra de rolagem."""
        util = px[c] - (PX_RESERVA if c == ultima else 0)
        fim = RESERVA_BARRA if c == ultima else ""
        if c in textos and c not in TEXTO_FIXO:
            return lambda v: cortar(formatadores[c](v), util) + fim
        return lambda v: formatadores[c](v) + fim

    visivel = df[list(colunas)].rename(columns=colunas)
    formatos = {colunas[c]: exibir(c) for c in colunas}
    config_colunas = {rotulo: st.column_config.Column(width=px[c], help=ajudas.get(c))
                      for c, rotulo in colunas.items()}
    selecao = {}
    if chave:
        selecao = {"on_select": ao_selecionar or "rerun", "selection_mode": "single-row", "key": chave}
        if selecao_padrao is not None:
            selecao["selection_default"] = selecao_padrao
    evento = st.dataframe(visivel.style.format(formatos), hide_index=True, width="stretch",
                          height=altura, column_config=config_colunas, placeholder=VAZIO, **selecao)
    if chave and evento.selection.rows:
        return evento.selection.rows[0]
    return None


def tabela_selecionavel(chave: str, df: pd.DataFrame, colunas: dict[str, str], coluna_id: str,
                        **formatos) -> int | None:
    """Tabela com seleção de UMA linha guardada pelo ID do registro (não pela posição).

    O st.dataframe guarda a seleção pela posição da linha. Se a ordem mudar (ex.: o nome
    editado muda a ordem alfabética), a mesma posição passaria a apontar para outro registro.
    Por isso:
      - o callback converte a posição clicada em ID, usando a lista de IDs que estava na tela;
      - a key da tabela inclui a ordem dos IDs: se a ordem muda, a tabela é "nova" e o
        selection_default remarca a linha do MESMO registro na posição nova.
    Devolve o ID selecionado (ou None).
    """
    ids = [int(i) for i in df[coluna_id]] if not df.empty else []
    chave_sel, chave_ids = f"_sel_{chave}", f"_ids_{chave}"

    selecionado = st.session_state.get(chave_sel)
    if selecionado not in ids:              # excluído ou escondido pela busca
        selecionado = None
        st.session_state[chave_sel] = None

    ordem = hashlib.md5(",".join(map(str, ids)).encode()).hexdigest()[:10]
    chave_tabela = f"tabela_{chave}_{versao_selecao(chave)}_{ordem}"
    st.session_state[chave_ids] = ids        # o que o usuário está vendo agora

    def ao_selecionar() -> None:
        linhas = st.session_state[chave_tabela]["selection"]["rows"]
        vistos = st.session_state.get(chave_ids, [])
        st.session_state[chave_sel] = vistos[linhas[0]] if linhas and linhas[0] < len(vistos) else None

    padrao = {"selection": {"rows": [ids.index(selecionado)]}} if selecionado is not None else None
    tabela(df, colunas, chave=chave_tabela, ao_selecionar=ao_selecionar, selecao_padrao=padrao, **formatos)
    return selecionado


def filtrar(df: pd.DataFrame, termo: str | None) -> pd.DataFrame:
    """Busca simples: mantém as linhas em que alguma coluna contém o termo."""
    termo = (termo or "").strip().casefold()
    if not termo or df.empty:
        return df
    achou = df.astype(str).apply(lambda col: col.str.casefold().str.contains(termo, regex=False))
    return df[achou.any(axis=1)]


def versao_selecao(chave: str) -> int:
    return st.session_state.setdefault(f"_versao_{chave}", 0)


def limpar_selecao(chave: str) -> None:
    """Desmarca a linha selecionada (esquece o ID e troca o key do dataframe)."""
    st.session_state[f"_versao_{chave}"] = versao_selecao(chave) + 1
    st.session_state[f"_sel_{chave}"] = None

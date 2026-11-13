"""Tabela formatada (R$, %, datas), busca e seleção de linha."""

from __future__ import annotations

import hashlib

import pandas as pd
import streamlit as st

from util.formatacao import brl, data_curta, data_hora, pct, qtd, texto
from util.i18n import t


def tabela(df: pd.DataFrame, colunas: dict[str, str], moeda=(), percentual=(),
           quantidade=(), datas=(), datas_curtas=(), altura="stretch", chave: str | None = None,
           larguras: dict[str, int] | None = None, ao_selecionar=None, selecao_padrao=None,
           ajudas: dict[str, str] | None = None):
    """st.dataframe com cabeçalhos em português e valores formatados (R$, %, datas).
    Com `chave`, permite selecionar uma linha e devolve a posição dela (ou None).
    `larguras` fixa a largura (px) de colunas específicas, ex.: {"produto": 180}.
    `ajudas` põe um tooltip no cabeçalho de colunas, ex.: {"total_pedido": "..."}."""
    if df.empty:
        st.info(t("comum.nenhum_registro"))
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
    largura = {}
    for grupo, px in ((moeda, 130), (datas, 135), (datas_curtas, 95), (percentual, 105),
                      (quantidade, 100)):
        for coluna in grupo:
            largura[coluna] = px
    largura.update(larguras or {})
    config_colunas = {}
    for coluna, rotulo in colunas.items():
        px, ajuda = largura.get(coluna), (ajudas or {}).get(coluna)
        if px or ajuda:
            config_colunas[rotulo] = st.column_config.Column(width=px, help=ajuda)
    selecao = {}
    if chave:
        selecao = {"on_select": ao_selecionar or "rerun", "selection_mode": "single-row", "key": chave}
        if selecao_padrao is not None:
            selecao["selection_default"] = selecao_padrao
    evento = st.dataframe(visivel.style.format(formatos), hide_index=True, width="stretch",
                          height=altura, column_config=config_colunas, **selecao)
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

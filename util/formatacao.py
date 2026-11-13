"""Formatação de valores para a tela, de acordo com o idioma (locale/<idioma>.json → "formato")
e limpeza de entradas. A moeda é sempre o real (R$); mudam os separadores e as datas:
  pt: R$ 1.234,56 · 12/11/2026      en: R$ 1,234.56 · 11/12/2026
"""

from __future__ import annotations

import re

import pandas as pd

from util.i18n import t


def vazio(v) -> bool:
    return v is None or (not isinstance(v, str) and pd.isna(v))


def _local(s: str) -> str:
    """Troca os separadores do padrão Python (1,234.56) pelos do idioma atual."""
    milhar, decimal = t("formato.milhar"), t("formato.decimal")
    return s.replace(",", "\0").replace(".", decimal).replace("\0", milhar)


def numero(v, casas: int = 2) -> str:
    return "" if vazio(v) else _local(f"{float(v):,.{casas}f}")


def brl(v) -> str:
    """R$ 1.234,56 (pt) / R$ 1,234.56 (en)"""
    return "" if vazio(v) else f"{t('formato.moeda')} {numero(v, 2)}"


def brl_curto(v) -> str:
    """R$ 123,8 mil (pt) / R$ 123.8K (en)"""
    v = float(v or 0)
    if v >= 1_000_000:
        return f"{t('formato.moeda')} {_local(f'{v / 1_000_000:.1f}')} {t('formato.milhao')}".replace(" M", "M")
    if v >= 1_000:
        return f"{t('formato.moeda')} {_local(f'{v / 1_000:.1f}')} {t('formato.mil')}".replace(" K", "K")
    return brl(v)


def pct(v) -> str:
    """5,00% (pt) / 5.00% (en)"""
    return "" if vazio(v) else _local(f"{float(v):.2f}") + "%"


def qtd(v) -> str:
    """Quantidades: 2 / 1,5 / 1.200 (pt)"""
    if vazio(v):
        return ""
    return _local(f"{float(v):,.3f}".rstrip("0").rstrip("."))


def data_hora(v) -> str:
    """12/11/2026 14:30 (pt) / 11/12/2026 14:30 (en)"""
    return "" if vazio(v) else pd.Timestamp(v).strftime(t("formato.data_hora"))


def data_curta(v) -> str:
    """12/11/2026 (pt) / 11/12/2026 (en)"""
    return "" if vazio(v) else pd.Timestamp(v).strftime(t("formato.data"))


def texto(v) -> str:
    return "" if vazio(v) else str(v)


def opcional(s: str | None) -> str | None:
    """Campo de texto vazio vira None (NULL no banco)."""
    s = (s or "").strip()
    return s or None


def so_digitos(s: str | None) -> str:
    """CPF/CNPJ digitado com pontos e traços -> só números."""
    return re.sub(r"\D", "", s or "")

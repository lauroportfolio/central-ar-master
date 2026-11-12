"""Formatação de valores para a tela (padrão brasileiro) e limpeza de entradas."""

from __future__ import annotations

import re

import pandas as pd


def vazio(v) -> bool:
    return v is None or (not isinstance(v, str) and pd.isna(v))


def _padrao_br(s: str) -> str:
    """1,234.56 -> 1.234,56"""
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def brl(v) -> str:
    """R$ 1.234,56"""
    return "" if vazio(v) else "R$ " + _padrao_br(f"{float(v):,.2f}")


def brl_curto(v) -> str:
    """R$ 123,8 mil / R$ 1,2 mi"""
    v = float(v or 0)
    if v >= 1_000_000:
        return "R$ " + _padrao_br(f"{v / 1_000_000:.1f}") + " mi"
    if v >= 1_000:
        return "R$ " + _padrao_br(f"{v / 1_000:.1f}") + " mil"
    return brl(v)


def pct(v) -> str:
    """5,00%"""
    return "" if vazio(v) else _padrao_br(f"{float(v):.2f}") + "%"


def qtd(v) -> str:
    """Quantidades: 2 / 1,5 / 1.200"""
    if vazio(v):
        return ""
    return _padrao_br(f"{float(v):,.3f}".rstrip("0").rstrip("."))


def data_hora(v) -> str:
    """12/11/2026 14:30"""
    return "" if vazio(v) else pd.Timestamp(v).strftime("%d/%m/%Y %H:%M")


def data_curta(v) -> str:
    """12/11/2026"""
    return "" if vazio(v) else pd.Timestamp(v).strftime("%d/%m/%Y")


def texto(v) -> str:
    return "" if vazio(v) else str(v)


def opcional(s: str | None) -> str | None:
    """Campo de texto vazio vira None (NULL no banco)."""
    s = (s or "").strip()
    return s or None


def so_digitos(s: str | None) -> str:
    """CPF/CNPJ digitado com pontos e traços -> só números."""
    return re.sub(r"\D", "", s or "")

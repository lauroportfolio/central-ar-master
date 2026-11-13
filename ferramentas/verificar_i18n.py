"""Verificações de tradução (rodar da raiz do projeto: python ferramentas/verificar_i18n.py).

1. locale/pt.json e locale/en.json têm exatamente as mesmas chaves (e os mesmos {marcadores}).
2. Varredura (AST) de app.py, paginas/ e componentes/: acusa strings literais que parecem
   texto de tela (deveriam vir de t("...")). Docstrings não contam. Para um literal que não é
   texto de tela (ex.: um script JS), marque a linha com o comentário  # i18n: ignorar
3. Toda chave literal usada em t("...") / t_plural("...") existe em pt.json.

Sai com código 1 se algo falhar (usado pelo teste E2E e2e/i18n.spec.ts).
"""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ALVOS = [RAIZ / "app.py", *sorted((RAIZ / "paginas").rglob("*.py")), *sorted((RAIZ / "componentes").rglob("*.py"))]
MARCA_IGNORAR = "# i18n: ignorar"


def achatar(arvore: dict, prefixo: str = "") -> dict[str, str]:
    saida = {}
    for chave, valor in arvore.items():
        caminho = f"{prefixo}.{chave}" if prefixo else chave
        if isinstance(valor, dict):
            saida.update(achatar(valor, caminho))
        else:
            saida[caminho] = valor
    return saida


def verificar_chaves() -> list[str]:
    pt = achatar(json.loads((RAIZ / "locale/pt.json").read_text(encoding="utf-8")))
    en = achatar(json.loads((RAIZ / "locale/en.json").read_text(encoding="utf-8")))
    erros = [f"só em pt.json: {c}" for c in sorted(pt.keys() - en.keys())]
    erros += [f"só em en.json: {c}" for c in sorted(en.keys() - pt.keys())]
    marcador = re.compile(r"\{(\w+)\}")
    for chave in sorted(pt.keys() & en.keys()):
        if set(marcador.findall(pt[chave])) != set(marcador.findall(en[chave])):
            erros.append(f"marcadores diferentes em {chave}: {pt[chave]!r} x {en[chave]!r}")
    print(f"[chaves] pt.json: {len(pt)} chaves · en.json: {len(en)} chaves · "
          f"{'iguais' if not erros else f'{len(erros)} diferença(s)'}")
    return erros


def parece_texto_de_tela(valor: str) -> bool:
    """Heurística: sobra alguma palavra depois de tirar tags HTML e {marcadores}?"""
    if re.fullmatch(r"#[0-9A-Fa-f]{3,8}", valor.strip()):
        return False                                   # cor: "#1E6FD9"
    # tira tags HTML (inclusive pedaços de tag abertos no meio de um f-string) e {marcadores}
    sem_marcacao = re.sub(r"<[^>]*>|<[^>]*$|^[^<>]*>|\{[^}]*\}", " ", valor).strip()
    if not re.search(r"[A-Za-zÀ-ÿ]{2,}", sem_marcacao):
        return False                                   # só números, símbolos, ícones, emoji
    # pedaços de atributos HTML (tabindex="0" aria-describedby=") não são texto
    sem_marcacao = re.sub(r'[\w-]+="[^"]*"?|"', " ", sem_marcacao).strip()
    if not sem_marcacao:
        return False
    if re.fullmatch(r"[a-z0-9_\-]+", sem_marcacao):
        return False                                   # identificadores: "primary", "id_pedido"
    if all("-" in palavra and palavra == palavra.lower() for palavra in sem_marcacao.split()):
        return False                                   # lista de classes CSS: "com-dica dica-"
    if " " not in sem_marcacao and re.search(r"[_.:/%]", sem_marcacao):
        return False                                   # chaves e códigos: "nav.inicio", ":material/add:", "regiao:N"
    return True


def docstrings(arvore: ast.AST) -> set[int]:
    ids = set()
    for no in ast.walk(arvore):
        if isinstance(no, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and no.body:
            primeiro = no.body[0]
            if isinstance(primeiro, ast.Expr) and isinstance(primeiro.value, ast.Constant):
                ids.add(id(primeiro.value))
    return ids


def verificar_literais() -> tuple[list[str], set[str]]:
    achados, chaves_usadas = [], set()
    for arquivo in ALVOS:
        fonte = arquivo.read_text(encoding="utf-8")
        linhas = fonte.splitlines()
        arvore = ast.parse(fonte)
        ignorar = docstrings(arvore)
        for no in ast.walk(arvore):
            # chaves usadas em t("...") / t_plural("...")
            if isinstance(no, ast.Call) and getattr(no.func, "id", None) in ("t", "t_plural") and no.args \
                    and isinstance(no.args[0], ast.Constant) and isinstance(no.args[0].value, str):
                chaves_usadas.add(no.args[0].value)
            if not (isinstance(no, ast.Constant) and isinstance(no.value, str)) or id(no) in ignorar:
                continue
            trecho = linhas[no.lineno - 1: (no.end_lineno or no.lineno)]
            anterior = linhas[no.lineno - 2] if no.lineno > 1 else ""
            if any(MARCA_IGNORAR in l for l in trecho) or MARCA_IGNORAR in anterior:
                continue
            if parece_texto_de_tela(no.value):
                achados.append(f"{arquivo.relative_to(RAIZ)}:{no.lineno}: {no.value[:70]!r}")
    print(f"[varredura] {len(ALVOS)} arquivos em app.py, paginas/ e componentes/ · "
          f"{len(achados)} string(s) visível(is) fora do idioma")
    return achados, chaves_usadas


def verificar_chaves_usadas(chaves: set[str]) -> list[str]:
    pt = achatar(json.loads((RAIZ / "locale/pt.json").read_text(encoding="utf-8")))
    grupos = {c.rsplit(".", 1)[0] for c in pt}           # para t_plural("status.pedidos", n)
    faltando = sorted(c for c in chaves if c not in pt and c not in grupos)
    print(f"[uso] {len(chaves)} chaves literais usadas no código · {len(faltando)} inexistente(s)")
    return [f"chave usada mas inexistente: {c}" for c in faltando]


def main() -> int:
    problemas = verificar_chaves()
    achados, usadas = verificar_literais()
    problemas += [f"string visível no código: {a}" for a in achados]
    problemas += verificar_chaves_usadas(usadas)
    for p in problemas:
        print("  ✗", p)
    print("OK: nenhuma pendência de tradução." if not problemas else f"FALHOU: {len(problemas)} pendência(s).")
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())

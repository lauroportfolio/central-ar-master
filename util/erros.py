"""Erro de banco compartilhado entre as camadas.

Fica em util/ (e não em dados/) para que as telas e os componentes possam
tratar o erro sem depender da camada de dados.
"""

from __future__ import annotations


class ErroBanco(Exception):
    """Erro vindo do SQL Server (ex.: THROW das procedures).

    mensagem   texto original (do banco ou do app), usado se não houver tradução
    codigo     número do THROW (50001...) quando houver — vira a chave erros.<codigo>
    chave      chave de tradução para erros que não são THROW (driver, conexão...)
    parametros valores para a mensagem traduzida (ex.: {"banco": "CentralDeAr"})
    """

    def __init__(self, mensagem: str, codigo: int | None = None, chave: str | None = None,
                 parametros: dict | None = None):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.codigo = codigo
        self.chave = chave
        self.parametros = parametros or {}

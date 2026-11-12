"""Erro de banco compartilhado entre as camadas.

Fica em util/ (e não em dados/) para que as telas e os componentes possam
tratar o erro sem depender da camada de dados.
"""


class ErroBanco(Exception):
    """Erro vindo do SQL Server (ex.: THROW das procedures) com mensagem legível."""

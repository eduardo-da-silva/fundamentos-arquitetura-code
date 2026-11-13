"""Interno do modulo Pagamentos -- os dados que `pagamentos` guarda.

Antes da extracao, a conciliacao cruzava as cobrancas com a tabela de
pedidos por um *join*. Depois dela, `pagamentos` so enxerga o que grava
aqui: uma copia local, escrita no momento da cobranca, com os campos de
que a conciliacao precisa e nenhum a mais. Nenhum outro modulo importa
este arquivo -- o esquema destes dados e de `pagamentos`.
"""

from dataclasses import dataclass

from mini_orion.pagamentos.api import ResultadoCobranca


@dataclass(frozen=True)
class RegistroCobranca:
    chave: str
    valor: float
    cartao_final: str  # so os quatro ultimos digitos: a conciliacao nao precisa do resto
    resultado: ResultadoCobranca


class RepositorioCobrancas:
    def __init__(self) -> None:
        self._registros: dict[str, RegistroCobranca] = {}

    def gravar(self, registro: RegistroCobranca) -> None:
        self._registros[registro.chave] = registro

    def todos(self) -> list[RegistroCobranca]:
        return list(self._registros.values())

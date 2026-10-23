"""Nucleo do microkernel de promocoes.

O nucleo conhece o CONTRATO de uma regra (`RegraDesconto`) e sabe
compor regras registradas. Nao conhece nenhuma regra concreta -- essas
vivem em `_regras/` e sao injetadas via `registrar`. Trocar, remover ou
somar promocoes nao toca este arquivo; e essa a promessa do microkernel.
"""

from dataclasses import dataclass
from typing import Protocol

from mini_orion.nucleo.modelos import Carrinho


@dataclass(frozen=True)
class Desconto:
    # Resultado imutavel: o motor devolve uma lista destes, sem somar
    # nem decidir prioridade. Compor o efeito final e de quem chama.
    origem: str
    valor: float


class RegraDesconto(Protocol):
    # O contrato que o nucleo enxerga. Um plugin e qualquer objeto com
    # este metodo -- nao ha classe base para herdar, so o formato.
    def avalia(self, carrinho: Carrinho) -> Desconto | None: ...


class MotorPromocoes:
    def __init__(self) -> None:
        self._regras: list[RegraDesconto] = []

    def registrar(self, regra: RegraDesconto) -> None:
        # Unica porta de entrada de plugins. Sem descoberta automatica,
        # sem entry points: quem monta o motor decide o que entra.
        self._regras.append(regra)

    def aplicar(self, carrinho: Carrinho) -> list[Desconto]:
        # Compoe as regras registradas na ordem de registro e descarta
        # as que nao se aplicam (retorno `None`).
        resultados = (regra.avalia(carrinho) for regra in self._regras)
        return [desconto for desconto in resultados if desconto is not None]

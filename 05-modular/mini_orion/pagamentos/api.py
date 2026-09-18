"""API publica do modulo Pagamentos.

Aqui ficam os contratos que os outros modulos podem enxergar: o
`Gateway` (Protocol), o `PedidoCobranca` (entrada) e o
`ResultadoCobranca` (saida). As implementacoes concretas -- os
provedores X, Y e o simulador de indisponibilidade -- vivem em
`_provedores.py` e nao sao importaveis de fora do pacote.

`compra` importa este modulo; nunca `pagamentos._provedores`. E este
modulo nao conhece `compra` nem `notificacoes` -- e o que os contratos
`independence` + `forbidden` de `setup.cfg` verificam.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class ResultadoCobranca(Enum):
    APROVADA = "aprovada"
    RECUSADA_PELO_EMISSOR = "recusada_pelo_emissor"
    ACIMA_DO_LIMITE = "acima_do_limite"
    PROVEDOR_INDISPONIVEL = "provedor_indisponivel"

    @property
    def deve_tentar_outro_provedor(self) -> bool:
        """A regra mora aqui, e nao espalhada pelos chamadores."""
        return self in {
            ResultadoCobranca.PROVEDOR_INDISPONIVEL,
            ResultadoCobranca.ACIMA_DO_LIMITE,
        }


@dataclass(frozen=True)
class PedidoCobranca:
    """Antes era a tupla (valor, cartao, parcelas).

    Connascencia de posicao: inverter dois campos passava no type
    checker e cobrava o valor errado. Com nomes, o erro e impossivel.
    """

    valor: float
    cartao: str
    parcelas: int = 1


class Gateway(Protocol):
    def cobrar(self, pedido: PedidoCobranca) -> ResultadoCobranca: ...

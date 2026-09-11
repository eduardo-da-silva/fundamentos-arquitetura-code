"""Contratos entre componentes.

Este modulo existe por um motivo estrutural: se o `checkout` importasse
`Notificador` de dentro de `notificacoes`, ele dependeria do modulo de
implementacao para alcancar o contrato — e nenhuma ferramenta
conseguiria distinguir "depende do contrato" de "depende da
implementacao", porque no nivel do `import` sao a mesma coisa.

Com os contratos aqui, a regra vira verificavel: `checkout` pode
importar `contratos`, e nao pode importar `pagamentos` nem
`notificacoes`. E exatamente isso que `setup.cfg` verifica.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from mini_orion.dominio.modelos import Carrinho, Cliente, Pedido

# --- Pagamentos ------------------------------------------------------------


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


# --- Notificacoes ----------------------------------------------------------


@dataclass(frozen=True)
class EventoNotificacao:
    destinatario: str
    assunto: str


class Notificador(Protocol):
    def publicar(self, evento: EventoNotificacao) -> None: ...


def evento_de_confirmacao(pedido: Pedido) -> EventoNotificacao:
    return EventoNotificacao(
        destinatario=pedido.cliente.email,
        assunto=f"Pedido {pedido.numero} confirmado",
    )


# --- Pedidos -------------------------------------------------------------------


class RepositorioDePedidos(Protocol):
    """Contrato de persistencia que a aplicacao enxerga.

    A aplicacao depende deste Protocol, no dominio; a classe concreta
    `RepositorioPedidos` (em memoria) mora na infraestrutura e o
    satisfaz por estrutura. Assim a camada de aplicacao nao precisa
    importar infraestrutura para tipar sua dependencia.
    """

    def emitir(
        self, carrinho: Carrinho, cliente: Cliente, total: float
    ) -> Pedido: ...

    def buscar(self, numero: str) -> Pedido | None: ...

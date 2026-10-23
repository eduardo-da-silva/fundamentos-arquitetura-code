"""API publica do modulo Notificacoes.

O que outro modulo pode enxergar: o contrato `Notificador` (Protocol), o
`EventoNotificacao` que ele transporta, a funcao `evento_de_confirmacao`
que monta o evento a partir de um `Pedido`, e a fabrica
`criar_notificador`, que devolve um `Notificador` ja montado sem expor
como ele e montado.

A fila e o decorador tolerante vivem em `_fila.py` e nao sao importaveis
de fora. `compra` chama `criar_notificador()`; nunca constroi o
`NotificacaoTolerante` na mao -- e por isso a fiacao das notificacoes
pode mudar sem tocar em `compra`.
"""

from dataclasses import dataclass
from typing import Protocol

from mini_orion.nucleo.modelos import Pedido


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


def criar_notificador() -> Notificador:
    """Monta o notificador padrao: fila em memoria dentro do decorador
    tolerante a falha.

    O import de `_fila` e local de proposito: `_fila` importa
    `EventoNotificacao` daqui, entao um import no topo fecharia um ciclo
    entre a API e o seu interno. A fabrica e o unico ponto do pacote que
    conhece as duas pecas ao mesmo tempo.
    """
    from mini_orion.notificacoes._fila import FilaNotificacoes, NotificacaoTolerante

    return NotificacaoTolerante(FilaNotificacoes())

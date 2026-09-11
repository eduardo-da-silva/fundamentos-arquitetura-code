"""Componente Notificacoes — implementacoes.

Os contratos (`Notificador`, `EventoNotificacao`) vivem no dominio. O
checkout nunca importa este modulo.
"""

from mini_orion.dominio import EventoNotificacao


class FilaNotificacoes:
    def __init__(self) -> None:
        self.pendentes: list[EventoNotificacao] = []

    def publicar(self, evento: EventoNotificacao) -> None:
        self.pendentes.append(evento)


class NotificacaoTolerante:
    """Decorador que absorve falha de qualquer notificador.

    Esta e a decisao arquitetural escrita em codigo: notificacao nunca
    derruba compra ja cobrada.

    O custo esta explicito no atributo `falhas` — existe uma janela em
    que o pedido esta confirmado e o cliente ainda nao sabe, e alguem
    precisa reprocessar essa lista. A decisao nao foi eliminar o
    problema, foi escolher qual problema ter.
    """

    def __init__(self, interno) -> None:
        self._interno = interno
        self.falhas: list[EventoNotificacao] = []

    def publicar(self, evento: EventoNotificacao) -> None:
        try:
            self._interno.publicar(evento)
        except Exception:
            self.falhas.append(evento)

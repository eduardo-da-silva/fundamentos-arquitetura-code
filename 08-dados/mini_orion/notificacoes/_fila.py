"""Interno do modulo Notificacoes — a fila em memoria e o decorador tolerante.

Os contratos (`Notificador`, `EventoNotificacao`) estao em
`notificacoes.api`. Ninguem de fora do pacote importa este modulo: quem
precisa de um notificador montado chama `notificacoes.api.criar_notificador()`.
"""

from mini_orion.notificacoes.api import EventoNotificacao, Notificador


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

    def __init__(self, interno: Notificador) -> None:
        self._interno = interno
        self.falhas: list[EventoNotificacao] = []

    def publicar(self, evento: EventoNotificacao) -> None:
        try:
            self._interno.publicar(evento)
        except Exception:
            self.falhas.append(evento)

    @property
    def pendentes(self) -> tuple[EventoNotificacao, ...]:
        """Visao somente-leitura do que foi entregue ao notificador interno.

        Existe para o teste inspecionar o resultado sem alcancar
        `servico._notificador._interno` — dois niveis de atributo
        privado. O `getattr` cobre o caso de o interno nao ter fila
        (um notificador qualquer): ai nao ha "pendentes" a mostrar.
        """
        return tuple(getattr(self._interno, "pendentes", ()))

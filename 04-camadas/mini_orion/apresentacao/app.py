"""Camada de apresentacao — a raiz de composicao (composition root).

Este e o unico modulo autorizado a importar `aplicacao` e
`infraestrutura` ao mesmo tempo: e aqui que as pecas concretas sao
escolhidas e ligadas ao caso de uso. Nenhuma camada abaixo sabe qual
gateway ou qual repositorio esta em uso.
"""

from mini_orion.aplicacao.checkout import ServicoCheckout
from mini_orion.dominio import Gateway
from mini_orion.infraestrutura.notificacoes import (
    FilaNotificacoes,
    NotificacaoTolerante,
)
from mini_orion.infraestrutura.pedidos import RepositorioPedidos


def montar_servico(
    gateway: Gateway, contingencia: Gateway | None = None
) -> ServicoCheckout:
    """Faz a fiacao do checkout com as implementacoes em memoria.

    Embrulha a fila de notificacoes no decorador tolerante — a decisao
    de que "notificacao nao derruba compra ja cobrada" e aplicada aqui,
    na montagem, e nao dentro do servico.
    """
    notificador = NotificacaoTolerante(FilaNotificacoes())
    return ServicoCheckout(
        gateway=gateway,
        pedidos=RepositorioPedidos(),
        notificador=notificador,
        gateway_contingencia=contingencia,
    )

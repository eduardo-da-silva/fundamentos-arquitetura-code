"""API publica do modulo Compra — o caso de uso "fechar pedido".

Compra e o modulo que coordena os outros. Por isso ele importa
`pagamentos.api` e `notificacoes.api` — e essa dependencia e honesta, nao
um vazamento: quem orquestra precisa conhecer o contrato de quem e
orquestrado. O que os contratos de `setup.cfg` proibem e outra coisa —
`compra` alcancar `pagamentos._provedores` ou `notificacoes._fila`,
passando por cima da API publica para tocar no concreto.

`pagamentos` e `notificacoes`, no sentido inverso, nao sabem que
`compra` existe (contrato `forbidden`) e nao se conhecem
(contrato `independence`).

O Protocol `RepositorioDePedidos` mora aqui, na API, e nao junto da
classe concreta: assim `ServicoCheckout` tipa a dependencia sem que o
pacote precise expor `compra._pedidos`.
"""

from typing import Protocol

from mini_orion.nucleo.modelos import Carrinho, Cliente, Pedido
from mini_orion.pagamentos.api import Gateway, PedidoCobranca, ResultadoCobranca
from mini_orion.notificacoes.api import (
    Notificador,
    criar_notificador,
    evento_de_confirmacao,
)
from mini_orion.compra._pedidos import RepositorioPedidos


class RepositorioDePedidos(Protocol):
    """Contrato de persistencia que o checkout enxerga.

    `ServicoCheckout` depende deste Protocol; a classe concreta
    `RepositorioPedidos` (em memoria) e interno de `compra` e o satisfaz
    por estrutura. Assim o servico nao precisa importar o concreto para
    tipar sua dependencia.
    """

    def emitir(
        self, carrinho: Carrinho, cliente: Cliente, total: float
    ) -> Pedido: ...

    def buscar(self, numero: str) -> Pedido | None: ...


class ServicoCheckout:
    def __init__(
        self,
        gateway: Gateway,
        pedidos: RepositorioDePedidos,
        notificador: Notificador,
        gateway_contingencia: Gateway | None = None,
    ) -> None:
        self._gateway = gateway
        self._pedidos = pedidos
        self._notificador = notificador
        self._contingencia = gateway_contingencia

    def fechar_pedido(self, carrinho: Carrinho, cliente: Cliente) -> str:
        cobranca = PedidoCobranca(valor=carrinho.total, cartao=cliente.cartao)

        resultado = self._gateway.cobrar(cobranca)

        # A decisao de tentar outro provedor pertence ao resultado, e nao
        # a uma cadeia de `if` aqui. Um novo motivo de falha se resolve
        # em pagamentos, sem tocar no checkout.
        if resultado.deve_tentar_outro_provedor and self._contingencia:
            resultado = self._contingencia.cobrar(cobranca)

        if resultado is not ResultadoCobranca.APROVADA:
            return resultado.value

        pedido = self._pedidos.emitir(carrinho, cliente, cobranca.valor)
        self._notificador.publicar(evento_de_confirmacao(pedido))

        return "confirmado"


def montar_servico(
    gateway: Gateway, contingencia: Gateway | None = None
) -> ServicoCheckout:
    """Raiz de composicao do checkout com as implementacoes em memoria.

    O repositorio concreto e interno de `compra` — a fabrica e o unico
    lugar que o instancia. O notificador vem de `criar_notificador()`:
    `compra` recebe um `Notificador` pronto e nunca monta o decorador
    tolerante na mao, entao a fiacao das notificacoes pode mudar sem
    tocar aqui. O gateway, sim, e injetado de fora — a escolha do
    provedor e de quem chama `montar_servico`.
    """
    return ServicoCheckout(
        gateway=gateway,
        pedidos=RepositorioPedidos(),
        notificador=criar_notificador(),
        gateway_contingencia=contingencia,
    )

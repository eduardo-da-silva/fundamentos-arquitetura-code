"""Interno do modulo Compra — o repositorio de pedidos em memoria.

Guarda o pedido emitido. E quem conhece o ciclo de vida — nao o
checkout, e nao pagamentos. Foi justamente isso que quebrou o ciclo
Pagamentos <-> Checkout do estado anterior.

Satisfaz por estrutura o Protocol `RepositorioDePedidos`, declarado na
API publica de `compra`. `ServicoCheckout` tipa a dependencia pelo
Protocol; a fabrica `montar_servico` — no mesmo pacote — e o unico ponto
que instancia esta classe concreta.
"""

from itertools import count

from mini_orion.nucleo.modelos import Carrinho, Cliente, Pedido


class RepositorioPedidos:
    def __init__(self) -> None:
        self._sequencia = count(1)
        self._pedidos: dict[str, Pedido] = {}

    def emitir(self, carrinho: Carrinho, cliente: Cliente, total: float) -> Pedido:
        numero = f"ORI-{next(self._sequencia):05d}"
        pedido = Pedido(numero=numero, cliente=cliente, total=total)
        self._pedidos[numero] = pedido
        return pedido

    def buscar(self, numero: str) -> Pedido | None:
        return self._pedidos.get(numero)

"""Repositorio de pedidos — implementacao em memoria (infraestrutura).

Guarda o pedido emitido. E quem conhece o ciclo de vida — nao o
checkout, e nao pagamentos. Foi justamente isso que quebrou o ciclo
Pagamentos <-> Checkout do estado anterior.

Satisfaz `mini_orion.dominio.RepositorioDePedidos` por estrutura: a
aplicacao tipa a dependencia pelo Protocol no dominio e nunca importa
esta classe.
"""

from itertools import count

from mini_orion.dominio import Carrinho, Cliente, Pedido


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

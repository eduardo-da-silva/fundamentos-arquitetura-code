"""Componente Checkout.

Compare com o estado 01-acoplado. O checkout continua dependendo de
quatro coisas — o acoplamento nao caiu. O que mudou foi a natureza da
dependencia: ele conhece capacidades (`Gateway`, `Notificador`), nao
implementacoes.

Muda por um motivo so: quando a sequencia do fechamento muda.
"""

from mini_orion.dominio import Carrinho, Cliente
from mini_orion.notificacoes import Notificador, evento_de_confirmacao
from mini_orion.pagamentos import Gateway
from mini_orion.pedidos import RepositorioPedidos


class ServicoCheckout:
    def __init__(
        self,
        gateway: Gateway,
        pedidos: RepositorioPedidos,
        notificador: Notificador,
    ) -> None:
        self._gateway = gateway
        self._pedidos = pedidos
        self._notificador = notificador

    def fechar_pedido(self, carrinho: Carrinho, cliente: Cliente) -> str:
        total = carrinho.total

        if not self._gateway.cobrar(total, cliente.cartao):
            return "recusado"

        pedido = self._pedidos.emitir(carrinho, cliente, total)

        # Fora do caminho critico: a compra ja esta valida neste ponto.
        evento = evento_de_confirmacao(pedido)
        self._notificador.publicar(evento)

        return "confirmado"

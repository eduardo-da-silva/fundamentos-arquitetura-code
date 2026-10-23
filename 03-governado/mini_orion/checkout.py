"""Componente Checkout — estado final do Mini-Orion no Modulo 1.

Repare nos imports: apenas `contratos`, `dominio` e `pedidos`. Nenhum
provedor de pagamento, nenhum servico de e-mail. A regra que impede a
volta desses imports esta em `setup.cfg` e roda com `lint-imports`.
"""

from mini_orion.contratos import (
    Gateway,
    Notificador,
    PedidoCobranca,
    ResultadoCobranca,
    evento_de_confirmacao,
)
from mini_orion.dominio import Carrinho, Cliente
from mini_orion.pedidos import RepositorioPedidos

class ServicoCheckout:
    def __init__(
        self,
        gateway: Gateway,
        pedidos: RepositorioPedidos,
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
        # em contratos.py, sem tocar no checkout.
        if resultado.deve_tentar_outro_provedor and self._contingencia:
            resultado = self._contingencia.cobrar(cobranca)

        if resultado is not ResultadoCobranca.APROVADA:
            return resultado.value

        pedido = self._pedidos.emitir(carrinho, cliente, cobranca.valor)
        self._notificador.publicar(evento_de_confirmacao(pedido))

        return "confirmado"

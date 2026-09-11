"""Componente Pagamentos — implementacoes.

Os contratos (`Gateway`, `PedidoCobranca`, `ResultadoCobranca`) vivem no
dominio. Aqui ficam apenas os provedores concretos, e nenhuma camada
acima da apresentacao importa este modulo.
"""

from mini_orion.dominio import PedidoCobranca, ResultadoCobranca


class GatewayPagamentoX:
    """Provedor principal."""

    LIMITE = 10_000.0

    def cobrar(self, pedido: PedidoCobranca) -> ResultadoCobranca:
        if pedido.valor > self.LIMITE:
            return ResultadoCobranca.ACIMA_DO_LIMITE
        if not pedido.cartao.startswith("4"):
            return ResultadoCobranca.RECUSADA_PELO_EMISSOR
        return ResultadoCobranca.APROVADA


class GatewayPagamentoY:
    """Provedor de contingencia contratado para as campanhas.

    Adicionar este provedor nao exigiu nenhuma alteracao no checkout.
    Essa e a medida pratica do valor da fronteira.
    """

    LIMITE = 5_000.0

    def cobrar(self, pedido: PedidoCobranca) -> ResultadoCobranca:
        if pedido.valor > self.LIMITE:
            return ResultadoCobranca.ACIMA_DO_LIMITE
        if len(pedido.cartao) < 10:
            return ResultadoCobranca.RECUSADA_PELO_EMISSOR
        return ResultadoCobranca.APROVADA


class GatewayForaDoAr:
    """Simula indisponibilidade do provedor, para exercitar contingencia."""

    def cobrar(self, pedido: PedidoCobranca) -> ResultadoCobranca:
        return ResultadoCobranca.PROVEDOR_INDISPONIVEL

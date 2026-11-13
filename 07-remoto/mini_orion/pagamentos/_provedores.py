"""Interno do modulo Pagamentos — os provedores concretos.

Os contratos (`Gateway`, `PedidoCobranca`, `ResultadoCobranca`) estao em
`pagamentos.api`. Aqui ficam apenas as implementacoes. O prefixo `_` no
nome do arquivo marca o limite: nenhum outro modulo importa
`pagamentos._provedores` — so a fabrica do proprio pacote e os testes de
isolamento dele.
"""

from mini_orion.pagamentos.api import PedidoCobranca, ResultadoCobranca


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


class GatewayPagamentoXv2(GatewayPagamentoX):
    """Provedor principal depois da v2: cobrancas altas ficam em analise.

    A analise antifraude e uma mudanca legitima do produtor. O que ela
    cria, para quem consome, e um valor de resultado que a v1 nao conhece.
    """

    LIMITE_SEM_ANALISE = 5_000.0

    def cobrar(self, pedido: PedidoCobranca) -> ResultadoCobranca:
        resultado = super().cobrar(pedido)
        if resultado is ResultadoCobranca.APROVADA and pedido.valor > self.LIMITE_SEM_ANALISE:
            return ResultadoCobranca.EM_ANALISE
        return resultado

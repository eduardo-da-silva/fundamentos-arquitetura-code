"""Cliente de Pagamentos -- o `Gateway` que fala pela rede.

Publico de proposito: e o que `compra` instancia no lugar do gateway
local. Satisfaz o mesmo `Gateway`, entao `ServicoCheckout` nao muda. E
esse o perigo: a assinatura `cobrar(pedido) -> ResultadoCobranca` e
identica a da chamada local, e esconde que agora ha um terceiro desfecho.

O formato da carga e lido e escrito aqui e, separadamente, em
`_servidor.py`: duas implementacoes do mesmo acordo.
"""

from mini_orion.pagamentos.api import (
    CobrancaIndeterminada,
    PedidoCobranca,
    ResultadoCobranca,
)
from mini_orion.rede.api import (
    TIMEOUT_POR_CHAMADA,
    Carga,
    TimeoutDeRede,
    Transporte,
)

DESTINO = "pagamentos"


class ClientePagamentos:
    def __init__(
        self,
        transporte: Transporte,
        tentativas: int = 2,
        timeout: float = TIMEOUT_POR_CHAMADA,
    ) -> None:
        self._transporte = transporte
        self._tentativas = tentativas
        self._timeout = timeout

    def cobrar(self, pedido: PedidoCobranca) -> ResultadoCobranca:
        carga = self._escrever(pedido)
        for _ in range(self._tentativas):
            try:
                resposta = self._transporte.chamar(DESTINO, "cobrar", carga, self._timeout)
            except TimeoutDeRede:
                continue  # repetir e seguro? Depende de a cobranca ser idempotente.
            return ResultadoCobranca(resposta["resultado"])
        raise CobrancaIndeterminada(f"{self._tentativas} tentativas sem resposta")

    def _escrever(self, pedido: PedidoCobranca) -> Carga:
        return {
            "valor": pedido.valor,
            "cartao": pedido.cartao,
            "parcelas": pedido.parcelas,
            "chave": pedido.chave.valor if pedido.chave else None,
        }

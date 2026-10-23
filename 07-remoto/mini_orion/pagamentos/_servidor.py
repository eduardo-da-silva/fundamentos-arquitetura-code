"""Interno do modulo Pagamentos -- o lado que atende pela rede.

`ServicoPagamentos` e o que, num sistema real, estaria atras de um
endereco: recebe uma carga, cobra no provedor e responde. Ele vive aqui,
como interno de `pagamentos`, e nenhum outro modulo o importa -- so o
ponto de montagem.

O formato da carga e lido e escrito AQUI e, separadamente, em
`cliente.py`. Sao duas implementacoes do mesmo acordo, como seriam em
dois repositorios. A Aula 19 mostra o que isso cobra.
"""

from mini_orion.nucleo.modelos import ChaveIdempotencia
from mini_orion.pagamentos.api import Gateway, PedidoCobranca, ResultadoCobranca
from mini_orion.rede.api import Carga

DESTINO = "pagamentos"


class ServicoPagamentos:
    def __init__(self, gateway: Gateway) -> None:
        self._gateway = gateway
        self._respostas_por_chave: dict[str, ResultadoCobranca] = {}
        # O que o extrato do provedor mostraria ao cliente: so cobrancas
        # aprovadas que de fato foram executadas.
        self.cobrancas_aprovadas: list[PedidoCobranca] = []

    def tratar_cobranca(self, carga: Carga) -> Carga:
        pedido = self._ler(carga)
        if pedido.chave and pedido.chave.valor in self._respostas_por_chave:
            # Repeticao reconhecida: devolve o que ja decidiu, sem cobrar de novo.
            return {"resultado": self._respostas_por_chave[pedido.chave.valor].value}
        resultado = self._gateway.cobrar(pedido)
        if resultado is ResultadoCobranca.APROVADA:
            self.cobrancas_aprovadas.append(pedido)
        if pedido.chave:
            self._respostas_por_chave[pedido.chave.valor] = resultado
        return {"resultado": resultado.value}

    def _ler(self, carga: Carga) -> PedidoCobranca:
        chave = carga.get("chave")
        return PedidoCobranca(
            valor=float(carga["valor"]),  # type: ignore[arg-type]
            cartao=str(carga["cartao"]),
            parcelas=int(carga.get("parcelas", 1)),  # type: ignore[call-overload]
            chave=ChaveIdempotencia(str(chave)) if chave else None,
        )

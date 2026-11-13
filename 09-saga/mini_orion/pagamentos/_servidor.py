"""Interno do modulo Pagamentos -- o lado que atende pela rede.

`ServicoPagamentos` e o que, num sistema real, estaria atras de um
endereco: recebe uma carga, cobra no provedor e responde. Ele vive aqui,
como interno de `pagamentos`, e nenhum outro modulo o importa -- so o
ponto de montagem.

O formato da carga e lido e escrito AQUI e, separadamente, em
`cliente.py`. Sao duas implementacoes do mesmo acordo, como seriam em
dois repositorios. A Aula 18 escreve o acordo em `contrato.py`.
"""

from mini_orion.nucleo.modelos import ChaveIdempotencia
from mini_orion.pagamentos._cobrancas import RegistroCobranca, RepositorioCobrancas
from mini_orion.pagamentos.conciliacao import Lancamento, RelatorioConciliacao, conciliar
from mini_orion.observabilidade.api import Registro
from mini_orion.pagamentos.api import (
    Gateway,
    PedidoCobranca,
    ResultadoCobranca,
    SituacaoCobranca,
)
from mini_orion.rede.api import Carga

DESTINO = "pagamentos"


class ServicoPagamentos:
    def __init__(
        self,
        gateway: Gateway,
        gravar_copia: bool = True,
        registro: Registro | None = None,
    ) -> None:
        self._gateway = gateway
        self._registro = registro
        self._estornadas: set[str] = set()
        self._gravar_copia = gravar_copia
        self.repositorio = RepositorioCobrancas()
        self._respostas_por_chave: dict[str, ResultadoCobranca] = {}
        # O que o extrato do provedor mostraria ao cliente: so cobrancas
        # aprovadas que de fato foram executadas.
        self.cobrancas_aprovadas: list[PedidoCobranca] = []

    @property
    def cobrancas_liquidas(self) -> list[PedidoCobranca]:
        """O que o cliente de fato pagou: aprovadas e nao estornadas."""
        return [
            c for c in self.cobrancas_aprovadas
            if not (c.chave and c.chave.valor in self._estornadas)
        ]

    def tratar_cobranca(self, carga: Carga) -> Carga:
        pedido = self._ler(carga)
        self._registrar("cobranca recebida", pedido.correlacao)
        if pedido.chave and pedido.chave.valor in self._respostas_por_chave:
            # Repeticao reconhecida: devolve o que ja decidiu, sem cobrar de novo.
            self._registrar("repeticao reconhecida", pedido.correlacao)
            return {"resultado": self._respostas_por_chave[pedido.chave.valor].value}
        resultado = self._gateway.cobrar(pedido)
        self._registrar(f"cobranca {resultado.value}", pedido.correlacao)
        if resultado is ResultadoCobranca.APROVADA:
            self.cobrancas_aprovadas.append(pedido)
        if pedido.chave:
            self._respostas_por_chave[pedido.chave.valor] = resultado
            if self._gravar_copia:
                # Copia local, no momento da cobranca: so o que a conciliacao le.
                self.repositorio.gravar(
                    RegistroCobranca(
                        chave=pedido.chave.valor,
                        valor=pedido.valor,
                        cartao_final=pedido.cartao[-4:],
                        resultado=resultado,
                    )
                )
        return {"resultado": resultado.value}

    def tratar_estorno(self, carga: Carga) -> Carga:
        chave, correlacao = str(carga["chave"]), self._correlacao(carga)
        if self._situacao(chave) is SituacaoCobranca.APROVADA:
            self._estornadas.add(chave)  # idempotente: estornar de novo nao estorna de novo
            self._registrar("estorno executado", correlacao)
        return {"situacao": self._situacao(chave).value}

    def tratar_consulta(self, carga: Carga) -> Carga:
        chave, correlacao = str(carga["chave"]), self._correlacao(carga)
        situacao = self._situacao(chave)
        self._registrar(f"consulta: {situacao.value}", correlacao)
        return {"situacao": situacao.value}

    def _situacao(self, chave: str) -> SituacaoCobranca:
        if chave in self._estornadas:
            return SituacaoCobranca.ESTORNADA
        if self._respostas_por_chave.get(chave) is ResultadoCobranca.APROVADA:
            return SituacaoCobranca.APROVADA
        return SituacaoCobranca.NAO_ENCONTRADA

    def _registrar(self, mensagem: str, correlacao: str | None) -> None:
        if self._registro:
            self._registro.registrar(mensagem, correlacao)

    @staticmethod
    def _correlacao(carga: Carga) -> str | None:
        valor = carga.get("correlacao")
        return str(valor) if valor else None

    def conciliar(self) -> RelatorioConciliacao:
        """Cruza a copia local com o extrato do provedor, sem consultar `compra`."""
        extrato = [
            Lancamento(chave=cobranca.chave.valor, valor=cobranca.valor)
            for cobranca in self.cobrancas_aprovadas
            if cobranca.chave
        ]
        return conciliar(self.repositorio.todos(), extrato)

    def _ler(self, carga: Carga) -> PedidoCobranca:
        chave = carga.get("chave")
        return PedidoCobranca(
            valor=float(carga["valor"]),  # type: ignore[arg-type]
            cartao=str(carga["cartao"]),
            parcelas=int(carga.get("parcelas", 1)),  # type: ignore[call-overload]
            chave=ChaveIdempotencia(str(chave)) if chave else None,
            correlacao=self._correlacao(carga),
        )

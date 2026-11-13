"""O fechamento como saga orquestrada.

Cobrar, emitir o pedido e notificar ja nao cabem numa transacao: a
cobranca esta em outro servico, com dado proprio. O orquestrador guarda
o estado do fechamento de forma explicita e, quando um passo depois da
cobranca falha, desfaz o que ja foi feito.

Os tres passos nao tem o mesmo papel:

- `cobrar` e compensavel: o estorno desfaz o efeito.
- `emitir` e o passo pivo: com o pedido emitido o fechamento so avanca.
  Se ele falha, compensa-se a cobranca.
- `notificar` e repetivel: se falha, o pedido continua valido e o aviso
  fica para ser reenviado. Nunca se desfaz uma compra por um e-mail.

Compensar nao e *rollback*. O cliente foi cobrado, e por um intervalo
viu a cobranca sem ter pedido. O estorno cria um fato novo; nao apaga o
anterior. Esse intervalo e a `janela` do resultado.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Callable
from uuid import uuid4

from mini_orion.nucleo.modelos import Carrinho, ChaveIdempotencia, Cliente
from mini_orion.notificacoes.api import (
    EventoNotificacao,
    FalhaDeNotificacao,
    Notificador,
    evento_de_confirmacao,
)
from mini_orion.observabilidade.api import Registro
from mini_orion.pagamentos.api import (
    CobrancaIndeterminada,
    GatewayComEstorno,
    OperacaoIndeterminada,
    PedidoCobranca,
    ResultadoCobranca,
    SituacaoCobranca,
)

# Hipotese de trabalho (Aula 20): o job de reconciliacao roda a cada 15 min.
INTERVALO_RECONCILIACAO = 900.0


class FalhaDeEmissao(Exception):
    """O pedido nao pode ser emitido depois de a cobranca ter sido aprovada."""


class MotivoPendencia(Enum):
    COBRANCA_INDETERMINADA = "cobranca_indeterminada"
    ESTORNO_PENDENTE = "estorno_pendente"


@dataclass
class Pendencia:
    chave: ChaveIdempotencia
    correlacao: str
    motivo: MotivoPendencia
    desde: float
    corrigida_em: float | None = None

    @property
    def janela(self) -> float | None:
        return None if self.corrigida_em is None else self.corrigida_em - self.desde


@dataclass(frozen=True)
class ResultadoFechamento:
    status: str
    chave: ChaveIdempotencia
    correlacao: str
    numero_pedido: str | None = None
    janela: float | None = None  # segundos com cliente cobrado e sem pedido, se houve compensacao


class OrquestradorFechamento:
    def __init__(
        self,
        gateway: GatewayComEstorno,
        pedidos,  # RepositorioDePedidos (Protocol de compra.api)
        notificador: Notificador,
        agora: Callable[[], float],
        registro: Registro | None = None,
        gerar_chave: Callable[[], ChaveIdempotencia] = ChaveIdempotencia.nova,
        gerar_correlacao: Callable[[], str | None] = lambda: str(uuid4()),
    ) -> None:
        self._gateway = gateway
        self._pedidos = pedidos
        self._notificador = notificador
        self._agora = agora
        self._registro = registro or Registro("compra", agora)
        self._gerar_chave = gerar_chave
        self._gerar_correlacao = gerar_correlacao
        self.pendencias: list[Pendencia] = []
        self.avisos_pendentes: list[EventoNotificacao] = []

    def fechar_pedido(self, carrinho: Carrinho, cliente: Cliente) -> ResultadoFechamento:
        chave, correlacao = self._gerar_chave(), self._gerar_correlacao()
        cobranca = PedidoCobranca(
            valor=carrinho.total, cartao=cliente.cartao, chave=chave, correlacao=correlacao
        )
        self._registrar("fechamento iniciado: cobrar", correlacao)
        try:
            resultado = self._gateway.cobrar(cobranca)
        except CobrancaIndeterminada:
            self._abrir_pendencia(chave, correlacao, MotivoPendencia.COBRANCA_INDETERMINADA)
            return ResultadoFechamento("cobranca_indeterminada", chave, correlacao)

        if resultado is not ResultadoCobranca.APROVADA:
            self._registrar(f"cobranca nao aprovada: {resultado.value}", correlacao)
            return ResultadoFechamento(resultado.value, chave, correlacao)

        cobrado_em = self._agora()
        try:
            pedido = self._pedidos.emitir(carrinho, cliente, cobranca.valor)
        except FalhaDeEmissao:
            self._registrar("emissao falhou: compensar", correlacao)
            return self._compensar(chave, correlacao, cobrado_em)

        self._registrar(f"pedido {pedido.numero} emitido", correlacao)
        self._notificar(evento_de_confirmacao(pedido), correlacao)
        return ResultadoFechamento("confirmado", chave, correlacao, pedido.numero)

    def reconciliar(self) -> list[Pendencia]:
        """Resolve as pendencias abertas e devolve as que foram corrigidas."""
        corrigidas = []
        for pendencia in [p for p in self.pendencias if p.corrigida_em is None]:
            try:
                situacao = self._gateway.consultar(pendencia.chave, pendencia.correlacao)
                if situacao is SituacaoCobranca.APROVADA:
                    self._gateway.estornar(pendencia.chave, pendencia.correlacao)
            except OperacaoIndeterminada:
                continue  # fica aberta para a proxima rodada
            pendencia.corrigida_em = self._agora()
            self._registrar("pendencia corrigida pela reconciliacao", pendencia.correlacao)
            corrigidas.append(pendencia)
        return corrigidas

    def _compensar(
        self, chave: ChaveIdempotencia, correlacao: str, cobrado_em: float
    ) -> ResultadoFechamento:
        try:
            self._gateway.estornar(chave, correlacao)
        except OperacaoIndeterminada:
            # A compensacao tambem pode falhar. Nao a repetimos em laco: abrimos pendencia.
            self._abrir_pendencia(chave, correlacao, MotivoPendencia.ESTORNO_PENDENTE)
            return ResultadoFechamento("compensacao_pendente", chave, correlacao)
        janela = self._agora() - cobrado_em
        self._registrar("compensado: cobranca estornada", correlacao)
        return ResultadoFechamento("compensado", chave, correlacao, janela=janela)

    def _notificar(self, evento: EventoNotificacao, correlacao: str | None) -> None:
        try:
            self._notificador.publicar(evento)
        except FalhaDeNotificacao:
            self.avisos_pendentes.append(evento)  # repetivel: o pedido nao se desfaz
            self._registrar("aviso falhou: guardado para reenvio", correlacao)

    def _abrir_pendencia(
        self, chave: ChaveIdempotencia, correlacao: str | None, motivo: MotivoPendencia
    ) -> None:
        self.pendencias.append(Pendencia(chave, correlacao or "", motivo, self._agora()))
        self._registrar(f"pendencia aberta: {motivo.value}", correlacao)

    def _registrar(self, mensagem: str, correlacao: str | None) -> None:
        self._registro.registrar(mensagem, correlacao)

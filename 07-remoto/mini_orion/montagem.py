"""Ponto de montagem do estado remoto.

Aqui, e so aqui, o sistema fica sabendo que `pagamentos` esta do outro
lado de uma rede: este arquivo registra o servidor na rede simulada,
cria o cliente e entrega ao `ServicoCheckout` um `Gateway` que ele nao
sabe distinguir de um local. Trocar o modo de comunicacao e mudar esta
funcao, e nenhum outro arquivo.
"""

from dataclasses import dataclass

from mini_orion.compra.api import GeradorDeChave, ServicoCheckout, montar_servico
from mini_orion.nucleo.modelos import ChaveIdempotencia
from mini_orion.pagamentos._provedores import GatewayPagamentoX
from mini_orion.pagamentos._servidor import DESTINO, ServicoPagamentos
from mini_orion.pagamentos.cliente import ClientePagamentos
from mini_orion.rede._simulada import RedeSimulada, RelogioSimulado
from mini_orion.rede.api import CAMPANHA, ParametrosRede


@dataclass
class CenarioRemoto:
    checkout: ServicoCheckout
    rede: RedeSimulada
    relogio: RelogioSimulado
    pagamentos: ServicoPagamentos


def montar_remoto(
    parametros: ParametrosRede = CAMPANHA,
    semente: int = 42,
    tentativas: int = 2,
    gerar_chave: GeradorDeChave = ChaveIdempotencia.nova,
) -> CenarioRemoto:
    relogio = RelogioSimulado()
    rede = RedeSimulada(relogio, parametros, semente)
    servidor = ServicoPagamentos(GatewayPagamentoX())
    rede.registrar(DESTINO, "cobrar", servidor.tratar_cobranca)
    cliente = ClientePagamentos(rede, tentativas=tentativas)
    checkout = montar_servico(cliente, gerar_chave=gerar_chave)
    return CenarioRemoto(checkout, rede, relogio, servidor)

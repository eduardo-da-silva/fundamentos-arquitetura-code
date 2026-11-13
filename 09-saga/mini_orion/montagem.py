"""Ponto de montagem do estado remoto.

Aqui, e so aqui, o sistema fica sabendo que `pagamentos` esta do outro
lado de uma rede: este arquivo registra o servidor na rede simulada,
cria o cliente e entrega ao `ServicoCheckout` um `Gateway` que ele nao
sabe distinguir de um local. Trocar o modo de comunicacao e mudar esta
funcao, e nenhum outro arquivo.
"""

from dataclasses import dataclass

from mini_orion.compra._pedidos import RepositorioPedidos
from mini_orion.compra.api import GeradorDeChave, ServicoCheckout, montar_servico
from mini_orion.compra.fechamento import OrquestradorFechamento
from mini_orion.notificacoes.api import Notificador, criar_notificador
from mini_orion.observabilidade.api import Registro
from mini_orion.nucleo.modelos import ChaveIdempotencia
from mini_orion.pagamentos._provedores import GatewayPagamentoX
from mini_orion.pagamentos.api import Gateway
from mini_orion.pagamentos.contrato import Leitor
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
    provedor: Gateway | None = None,
    leitor: Leitor | None = None,
    gravar_copia: bool = True,
) -> CenarioRemoto:
    relogio = RelogioSimulado()
    rede = RedeSimulada(relogio, parametros, semente)
    servidor = ServicoPagamentos(provedor or GatewayPagamentoX(), gravar_copia)
    rede.registrar(DESTINO, "cobrar", servidor.tratar_cobranca)
    if leitor is None:
        cliente = ClientePagamentos(rede, tentativas=tentativas)
    else:
        cliente = ClientePagamentos(rede, tentativas=tentativas, leitor=leitor)
    checkout = montar_servico(cliente, gerar_chave=gerar_chave)
    return CenarioRemoto(checkout, rede, relogio, servidor)


@dataclass
class CenarioSaga:
    orquestrador: OrquestradorFechamento
    rede: RedeSimulada
    relogio: RelogioSimulado
    pagamentos: ServicoPagamentos
    registro_compra: Registro
    registro_pagamentos: Registro


def montar_saga(
    parametros: ParametrosRede = CAMPANHA,
    semente: int = 42,
    tentativas: int = 2,
    pedidos=None,
    notificador: Notificador | None = None,
    gerar_correlacao=None,
) -> CenarioSaga:
    """Monta o fechamento como saga. `pedidos` e `notificador` aceitam
    substitutos, para injetar falha em cada passo."""
    relogio = RelogioSimulado()
    rede = RedeSimulada(relogio, parametros, semente)
    registro_compra = Registro("compra", relogio.agora)
    registro_pagamentos = Registro("pagamentos", relogio.agora)
    servidor = ServicoPagamentos(GatewayPagamentoX(), registro=registro_pagamentos)
    for operacao, tratador in (
        ("cobrar", servidor.tratar_cobranca),
        ("estornar", servidor.tratar_estorno),
        ("consultar", servidor.tratar_consulta),
    ):
        rede.registrar(DESTINO, operacao, tratador)
    cliente = ClientePagamentos(rede, tentativas=tentativas)
    argumentos = {} if gerar_correlacao is None else {"gerar_correlacao": gerar_correlacao}
    orquestrador = OrquestradorFechamento(
        gateway=cliente,
        pedidos=pedidos or RepositorioPedidos(),
        notificador=notificador or criar_notificador(),
        agora=relogio.agora,
        registro=registro_compra,
        **argumentos,
    )
    return CenarioSaga(orquestrador, rede, relogio, servidor, registro_compra, registro_pagamentos)

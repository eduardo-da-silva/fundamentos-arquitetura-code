"""O fechamento como saga: o que acontece quando cada passo falha.

A matriz injeta uma falha por vez e confere tres coisas: o que o
orquestrador responde, quanto o cliente pagou no fim e se existe pedido.
"""

import pytest

from mini_orion.compra.api import ServicoCheckout
from mini_orion.compra.fechamento import (
    INTERVALO_RECONCILIACAO,
    FalhaDeEmissao,
    MotivoPendencia,
)
from mini_orion.compra._pedidos import RepositorioPedidos
from mini_orion.montagem import CenarioSaga, montar_saga
from mini_orion.nucleo.modelos import Carrinho, Cliente, ItemCarrinho
from mini_orion.notificacoes.api import EventoNotificacao, FalhaDeNotificacao
from mini_orion.pagamentos.cliente import ClientePagamentos
from mini_orion.rede.api import TIMEOUT_DO_FECHAMENTO, Falha


class PedidosQueFalham(RepositorioPedidos):
    def emitir(self, carrinho, cliente, total):
        raise FalhaDeEmissao("banco de pedidos indisponivel")


class NotificadorQueFalha:
    def publicar(self, evento: EventoNotificacao) -> None:
        raise FalhaDeNotificacao("servico de e-mail fora do ar")


@pytest.fixture
def carrinho() -> Carrinho:
    return Carrinho(itens=[ItemCarrinho(sku="TEC-01", preco_unitario=150.0, quantidade=2)])


@pytest.fixture
def cliente() -> Cliente:
    return Cliente(nome="Maria", email="maria@exemplo.com", cartao="4111111111")


def liquidas(cenario: CenarioSaga) -> int:
    return len(cenario.pagamentos.cobrancas_liquidas)


def test_sem_saga_a_falha_na_emissao_deixa_o_cliente_cobrado_sem_pedido(
    carrinho: Carrinho, cliente: Cliente
) -> None:
    cenario = montar_saga(pedidos=PedidosQueFalham())
    cenario.rede.forcar(None)
    checkout = ServicoCheckout(
        gateway=ClientePagamentos(cenario.rede),
        pedidos=PedidosQueFalham(),
        notificador=NotificadorQueFalha(),
    )

    with pytest.raises(FalhaDeEmissao):
        checkout.fechar_pedido(carrinho, cliente)

    assert liquidas(cenario) == 1  # cobrado, e nenhum pedido: o suporte estorna a mao


def test_o_caminho_feliz_confirma(carrinho: Carrinho, cliente: Cliente) -> None:
    cenario = montar_saga()
    cenario.rede.forcar(None)

    resultado = cenario.orquestrador.fechar_pedido(carrinho, cliente)

    assert resultado.status == "confirmado"
    assert resultado.numero_pedido is not None
    assert liquidas(cenario) == 1
    assert cenario.orquestrador.pendencias == []


# --- a matriz: uma falha por passo ----------------------------------------


def test_falha_na_emissao_compensa_com_estorno(carrinho: Carrinho, cliente: Cliente) -> None:
    cenario = montar_saga(pedidos=PedidosQueFalham())
    cenario.rede.forcar(None, None)  # cobrar e estornar respondem

    resultado = cenario.orquestrador.fechar_pedido(carrinho, cliente)

    assert resultado.status == "compensado"
    assert resultado.numero_pedido is None
    assert liquidas(cenario) == 0  # o cliente nao paga por um pedido que nao existe


def test_a_janela_da_compensacao_imediata_cabe_no_timeout_do_fechamento(
    carrinho: Carrinho, cliente: Cliente
) -> None:
    cenario = montar_saga(pedidos=PedidosQueFalham())
    cenario.rede.forcar(None, None)

    resultado = cenario.orquestrador.fechar_pedido(carrinho, cliente)

    assert 0 < resultado.janela < TIMEOUT_DO_FECHAMENTO


def test_resposta_do_estorno_perdida_nao_estorna_duas_vezes(
    carrinho: Carrinho, cliente: Cliente
) -> None:
    cenario = montar_saga(pedidos=PedidosQueFalham())
    cenario.rede.forcar(None, Falha.PERDA_NA_VOLTA, None)  # o estorno executa; a resposta se perde; a repeticao e reconhecida

    resultado = cenario.orquestrador.fechar_pedido(carrinho, cliente)

    assert resultado.status == "compensado"
    assert liquidas(cenario) == 0


def test_compensacao_que_falha_vira_pendencia_e_a_reconciliacao_a_resolve(
    carrinho: Carrinho, cliente: Cliente
) -> None:
    cenario = montar_saga(pedidos=PedidosQueFalham())
    cenario.rede.forcar(None, Falha.PERDA_NA_IDA, Falha.PERDA_NA_IDA)  # cobra, e o estorno nao chega

    resultado = cenario.orquestrador.fechar_pedido(carrinho, cliente)

    assert resultado.status == "compensacao_pendente"
    assert liquidas(cenario) == 1  # cobrado e sem pedido, por enquanto
    [pendencia] = cenario.orquestrador.pendencias
    assert pendencia.motivo is MotivoPendencia.ESTORNO_PENDENTE

    cenario.relogio.avancar(INTERVALO_RECONCILIACAO)
    cenario.rede.forcar(None, None)
    cenario.orquestrador.reconciliar()

    assert liquidas(cenario) == 0
    assert pendencia.corrigida_em is not None


def test_cobranca_perdida_na_ida_nao_cobra_e_a_reconciliacao_so_fecha_a_pendencia(
    carrinho: Carrinho, cliente: Cliente
) -> None:
    cenario = montar_saga()
    cenario.rede.forcar(Falha.PERDA_NA_IDA, Falha.PERDA_NA_IDA)

    resultado = cenario.orquestrador.fechar_pedido(carrinho, cliente)

    assert resultado.status == "cobranca_indeterminada"
    assert liquidas(cenario) == 0

    cenario.relogio.avancar(INTERVALO_RECONCILIACAO)
    cenario.rede.forcar(None)  # a consulta responde: nao ha cobranca
    corrigidas = cenario.orquestrador.reconciliar()

    assert len(corrigidas) == 1
    assert liquidas(cenario) == 0


def test_cobranca_perdida_na_volta_cobrou_e_a_reconciliacao_estorna(
    carrinho: Carrinho, cliente: Cliente
) -> None:
    cenario = montar_saga()
    cenario.rede.forcar(Falha.PERDA_NA_VOLTA, Falha.PERDA_NA_VOLTA)

    resultado = cenario.orquestrador.fechar_pedido(carrinho, cliente)

    assert resultado.status == "cobranca_indeterminada"
    assert liquidas(cenario) == 1  # cobrado, ninguem sabe

    cenario.relogio.avancar(INTERVALO_RECONCILIACAO)
    cenario.rede.forcar(None, None)  # consulta e estorno respondem
    cenario.orquestrador.reconciliar()

    assert liquidas(cenario) == 0


def test_a_janela_ate_a_reconciliacao_e_a_ordem_do_intervalo(
    carrinho: Carrinho, cliente: Cliente
) -> None:
    cenario = montar_saga()
    cenario.rede.forcar(Falha.PERDA_NA_VOLTA, Falha.PERDA_NA_VOLTA)
    cenario.orquestrador.fechar_pedido(carrinho, cliente)

    cenario.relogio.avancar(INTERVALO_RECONCILIACAO)
    cenario.rede.forcar(None, None)
    [corrigida] = cenario.orquestrador.reconciliar()

    assert INTERVALO_RECONCILIACAO <= corrigida.janela <= INTERVALO_RECONCILIACAO + 1.0


def test_reconciliacao_sem_resposta_deixa_a_pendencia_aberta(
    carrinho: Carrinho, cliente: Cliente
) -> None:
    cenario = montar_saga()
    cenario.rede.forcar(Falha.PERDA_NA_VOLTA, Falha.PERDA_NA_VOLTA)
    cenario.orquestrador.fechar_pedido(carrinho, cliente)

    cenario.rede.forcar(Falha.PERDA_NA_IDA, Falha.PERDA_NA_IDA)  # a consulta tambem se perde
    corrigidas = cenario.orquestrador.reconciliar()

    assert corrigidas == []
    assert cenario.orquestrador.pendencias[0].corrigida_em is None


def test_falha_na_notificacao_nao_desfaz_o_pedido(carrinho: Carrinho, cliente: Cliente) -> None:
    cenario = montar_saga(notificador=NotificadorQueFalha())
    cenario.rede.forcar(None)

    resultado = cenario.orquestrador.fechar_pedido(carrinho, cliente)

    assert resultado.status == "confirmado"
    assert liquidas(cenario) == 1
    assert len(cenario.orquestrador.avisos_pendentes) == 1  # repetivel: sera reenviado


def test_estornar_duas_vezes_estorna_uma(carrinho: Carrinho, cliente: Cliente) -> None:
    cenario = montar_saga(pedidos=PedidosQueFalham())
    cenario.rede.forcar(None, None, None)
    resultado = cenario.orquestrador.fechar_pedido(carrinho, cliente)

    cliente_pg = ClientePagamentos(cenario.rede)
    cliente_pg.estornar(resultado.chave)

    assert liquidas(cenario) == 0
    executados = [e for e in cenario.registro_pagamentos.eventos if e.mensagem == "estorno executado"]
    assert len(executados) == 1  # a segunda chamada foi reconhecida e nao estornou de novo

"""Cada modulo de dominio se testa sem instanciar os outros."""

from mini_orion.pagamentos.api import PedidoCobranca, ResultadoCobranca
from mini_orion.pagamentos._provedores import GatewayPagamentoX
from mini_orion.notificacoes.api import EventoNotificacao
from mini_orion.notificacoes._fila import FilaNotificacoes, NotificacaoTolerante


def test_pagamentos_isolado() -> None:
    resultado = GatewayPagamentoX().cobrar(PedidoCobranca(valor=100.0, cartao="4111111111"))
    assert resultado is ResultadoCobranca.APROVADA


def test_notificacoes_isolado() -> None:
    fila = FilaNotificacoes()
    NotificacaoTolerante(fila).publicar(EventoNotificacao(destinatario="a@b.c", assunto="x"))
    assert len(fila.pendentes) == 1

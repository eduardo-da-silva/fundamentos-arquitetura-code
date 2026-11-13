"""Reconstruir o caminho de um fechamento que falhou.

Dois servicos, dois registros. O identificador de correlacao e o que
permite juntar as linhas de cada um na mesma historia.
"""

import pytest

from mini_orion.compra.fechamento import INTERVALO_RECONCILIACAO, FalhaDeEmissao
from mini_orion.compra._pedidos import RepositorioPedidos
from mini_orion.montagem import montar_saga
from mini_orion.nucleo.modelos import Carrinho, Cliente, ItemCarrinho
from mini_orion.observabilidade.api import reconstruir
from mini_orion.rede.api import Falha


class PedidosQueFalham(RepositorioPedidos):
    def emitir(self, carrinho, cliente, total):
        raise FalhaDeEmissao("banco de pedidos indisponivel")


@pytest.fixture
def carrinho() -> Carrinho:
    return Carrinho(itens=[ItemCarrinho(sku="TEC-01", preco_unitario=150.0, quantidade=2)])


@pytest.fixture
def cliente() -> Cliente:
    return Cliente(nome="Maria", email="maria@exemplo.com", cartao="4111111111")


def caminho(eventos) -> list[tuple[str, str]]:
    return [(e.origem, e.mensagem) for e in eventos]


def test_sem_identificador_os_dois_registros_nao_se_juntam(
    carrinho: Carrinho, cliente: Cliente
) -> None:
    cenario = montar_saga(pedidos=PedidosQueFalham(), gerar_correlacao=lambda: None)
    cenario.rede.forcar(None, None)

    cenario.orquestrador.fechar_pedido(carrinho, cliente)

    assert cenario.registro_compra.eventos and cenario.registro_pagamentos.eventos
    assert all(e.correlacao is None for e in cenario.registro_compra.eventos)
    assert all(e.correlacao is None for e in cenario.registro_pagamentos.eventos)
    # nenhuma busca por identificador devolve a historia
    assert reconstruir("qualquer", cenario.registro_compra, cenario.registro_pagamentos) == []


def test_com_o_identificador_o_caminho_do_fechamento_que_falhou_se_reconstroi(
    carrinho: Carrinho, cliente: Cliente
) -> None:
    cenario = montar_saga(pedidos=PedidosQueFalham())
    cenario.rede.forcar(None, None)

    resultado = cenario.orquestrador.fechar_pedido(carrinho, cliente)

    eventos = reconstruir(
        resultado.correlacao, cenario.registro_compra, cenario.registro_pagamentos
    )
    assert caminho(eventos) == [
        ("compra", "fechamento iniciado: cobrar"),
        ("pagamentos", "cobranca recebida"),
        ("pagamentos", "cobranca aprovada"),
        ("compra", "emissao falhou: compensar"),
        ("pagamentos", "estorno executado"),
        ("compra", "compensado: cobranca estornada"),
    ]


def test_o_caminho_inclui_a_reconciliacao_que_corrigiu_depois(
    carrinho: Carrinho, cliente: Cliente
) -> None:
    cenario = montar_saga()
    cenario.rede.forcar(Falha.PERDA_NA_VOLTA, Falha.PERDA_NA_VOLTA)
    resultado = cenario.orquestrador.fechar_pedido(carrinho, cliente)
    cenario.relogio.avancar(INTERVALO_RECONCILIACAO)
    cenario.rede.forcar(None, None)
    cenario.orquestrador.reconciliar()

    eventos = reconstruir(
        resultado.correlacao, cenario.registro_compra, cenario.registro_pagamentos
    )

    mensagens = [e.mensagem for e in eventos]
    assert mensagens[-1] == "pendencia corrigida pela reconciliacao"
    assert "estorno executado" in mensagens
    assert eventos[-1].instante - eventos[0].instante >= INTERVALO_RECONCILIACAO


def test_fechamentos_diferentes_nao_se_misturam(carrinho: Carrinho, cliente: Cliente) -> None:
    cenario = montar_saga(pedidos=PedidosQueFalham())
    cenario.rede.forcar(None, None, None, None)
    primeiro = cenario.orquestrador.fechar_pedido(carrinho, cliente)
    segundo = cenario.orquestrador.fechar_pedido(carrinho, cliente)

    eventos = reconstruir(primeiro.correlacao, cenario.registro_compra, cenario.registro_pagamentos)

    assert primeiro.correlacao != segundo.correlacao
    assert len(eventos) == 6

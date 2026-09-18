"""Testes do estado governado, agora sobre a estrutura modular por dominio.

Alem de verificar comportamento, alguns destes testes verificam
DECISOES — e falham se a decisao for desfeita, mesmo que o sistema
continue funcionando. A fitness function da estrutura (quem pode
importar quem) mudou-se para `test_modular.py`.
"""

import pytest

from mini_orion.compra.api import ServicoCheckout, montar_servico
from mini_orion.nucleo.modelos import Carrinho, Cliente, ItemCarrinho
from mini_orion.notificacoes.api import EventoNotificacao
from mini_orion.notificacoes._fila import NotificacaoTolerante
from mini_orion.pagamentos.api import ResultadoCobranca
from mini_orion.pagamentos._provedores import (
    GatewayForaDoAr,
    GatewayPagamentoX,
    GatewayPagamentoY,
)
from mini_orion.compra._pedidos import RepositorioPedidos


@pytest.fixture
def carrinho() -> Carrinho:
    return Carrinho(
        itens=[
            ItemCarrinho(sku="TEC-01", preco_unitario=150.0, quantidade=2),
            ItemCarrinho(sku="MOU-07", preco_unitario=80.0, quantidade=1),
        ]
    )


@pytest.fixture
def cliente() -> Cliente:
    return Cliente(nome="Maria", email="maria@exemplo.com", cartao="4111111111")


def montar(gateway, contingencia=None):
    """Usa a raiz de composicao e devolve tambem o notificador montado.

    `montar_servico` faz a fiacao; os testes de comportamento precisam
    inspecionar a fila de notificacoes e as falhas absorvidas. O
    notificador expoe isso pela sua propria superficie publica
    (`pendentes`, `falhas`), entao o helper para em UM nivel de atributo
    privado (`servico._notificador`) — nao dois, como antes.
    """
    servico = montar_servico(gateway, contingencia)
    return servico, servico._notificador


# --- Comportamento ---------------------------------------------------------


def test_fecha_pedido(carrinho, cliente) -> None:
    servico, notificador = montar(GatewayPagamentoX())

    assert servico.fechar_pedido(carrinho, cliente) == "confirmado"
    assert len(notificador.pendentes) == 1


def test_recusa_informa_o_motivo(carrinho) -> None:
    """Antes o retorno era so 'recusado'. Agora o motivo e distinguivel."""
    servico, _ = montar(GatewayPagamentoX())
    cliente = Cliente(nome="Joao", email="joao@exemplo.com", cartao="5111111111")

    assert servico.fechar_pedido(carrinho, cliente) == "recusada_pelo_emissor"


def test_acima_do_limite_e_recusa_do_emissor_sao_distinguiveis(cliente) -> None:
    servico, _ = montar(GatewayPagamentoX())
    caro = Carrinho(
        itens=[ItemCarrinho(sku="SRV-99", preco_unitario=20_000.0, quantidade=1)]
    )

    assert servico.fechar_pedido(caro, cliente) == "acima_do_limite"


def test_usa_contingencia_quando_provedor_esta_fora(carrinho, cliente) -> None:
    servico, notificador = montar(GatewayForaDoAr(), contingencia=GatewayPagamentoY())

    assert servico.fechar_pedido(carrinho, cliente) == "confirmado"
    assert len(notificador.pendentes) == 1


def test_troca_de_provedor_nao_altera_checkout(carrinho, cliente) -> None:
    com_x, _ = montar(GatewayPagamentoX())
    com_y, _ = montar(GatewayPagamentoY())

    assert com_x.fechar_pedido(carrinho, cliente) == "confirmado"
    assert com_y.fechar_pedido(carrinho, cliente) == "confirmado"


# --- Decisoes arquiteturais ------------------------------------------------


def test_falha_de_notificacao_nao_invalida_a_compra(carrinho, cliente) -> None:
    """No estado 02-fronteiras este teste falhava. A fronteira estava incompleta."""

    class NotificadorQuebrado:
        def publicar(self, evento: EventoNotificacao) -> None:
            raise RuntimeError("servico de e-mail indisponivel")

    tolerante = NotificacaoTolerante(NotificadorQuebrado())
    servico = ServicoCheckout(
        gateway=GatewayPagamentoX(),
        pedidos=RepositorioPedidos(),
        notificador=tolerante,
    )

    assert servico.fechar_pedido(carrinho, cliente) == "confirmado"
    # O custo da decisao fica visivel: o aviso ficou pendente.
    assert len(tolerante.falhas) == 1


def test_resultado_concentra_a_regra_de_contingencia() -> None:
    """A decisao de tentar outro provedor nao pode vazar para o checkout."""
    assert ResultadoCobranca.PROVEDOR_INDISPONIVEL.deve_tentar_outro_provedor
    assert ResultadoCobranca.ACIMA_DO_LIMITE.deve_tentar_outro_provedor
    assert not ResultadoCobranca.RECUSADA_PELO_EMISSOR.deve_tentar_outro_provedor
    assert not ResultadoCobranca.APROVADA.deve_tentar_outro_provedor


def test_pedido_de_cobranca_e_imutavel_e_nomeado() -> None:
    """Connascencia de posicao eliminada: campos por nome, objeto congelado."""
    from dataclasses import FrozenInstanceError

    from mini_orion.pagamentos.api import PedidoCobranca

    cobranca = PedidoCobranca(valor=380.0, cartao="4111111111")

    assert cobranca.parcelas == 1
    with pytest.raises(FrozenInstanceError):
        cobranca.valor = 1.0  # type: ignore[misc]

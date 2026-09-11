"""Testes do estado governado, agora sobre a estrutura em camadas.

Alem de verificar comportamento, alguns destes testes verificam
DECISOES — e falham se a decisao for desfeita, mesmo que o sistema
continue funcionando. Sao a primeira aparicao de fitness function no
curso.
"""

import pytest

from mini_orion.aplicacao.checkout import ServicoCheckout
from mini_orion.apresentacao.app import montar_servico
from mini_orion.dominio import (
    Carrinho,
    Cliente,
    EventoNotificacao,
    ItemCarrinho,
    ResultadoCobranca,
)
from mini_orion.infraestrutura.notificacoes import NotificacaoTolerante
from mini_orion.infraestrutura.pagamentos import (
    GatewayForaDoAr,
    GatewayPagamentoX,
    GatewayPagamentoY,
)
from mini_orion.infraestrutura.pedidos import RepositorioPedidos


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
    """Usa a raiz de composicao e devolve tambem a fila e o decorador.

    `montar_servico` faz a fiacao; os testes de comportamento precisam
    inspecionar a fila de notificacoes e as falhas absorvidas, entao
    alcancamos as pecas montadas pelo notificador ja injetado.
    """
    servico = montar_servico(gateway, contingencia)
    tolerante = servico._notificador
    fila = tolerante._interno
    return servico, fila, tolerante


# --- Comportamento ---------------------------------------------------------


def test_fecha_pedido(carrinho, cliente) -> None:
    servico, fila, _ = montar(GatewayPagamentoX())

    assert servico.fechar_pedido(carrinho, cliente) == "confirmado"
    assert len(fila.pendentes) == 1


def test_recusa_informa_o_motivo(carrinho) -> None:
    """Antes o retorno era so 'recusado'. Agora o motivo e distinguivel."""
    servico, _, _ = montar(GatewayPagamentoX())
    cliente = Cliente(nome="Joao", email="joao@exemplo.com", cartao="5111111111")

    assert servico.fechar_pedido(carrinho, cliente) == "recusada_pelo_emissor"


def test_acima_do_limite_e_recusa_do_emissor_sao_distinguiveis(cliente) -> None:
    servico, _, _ = montar(GatewayPagamentoX())
    caro = Carrinho(
        itens=[ItemCarrinho(sku="SRV-99", preco_unitario=20_000.0, quantidade=1)]
    )

    assert servico.fechar_pedido(caro, cliente) == "acima_do_limite"


def test_usa_contingencia_quando_provedor_esta_fora(carrinho, cliente) -> None:
    servico, fila, _ = montar(GatewayForaDoAr(), contingencia=GatewayPagamentoY())

    assert servico.fechar_pedido(carrinho, cliente) == "confirmado"
    assert len(fila.pendentes) == 1


def test_troca_de_provedor_nao_altera_checkout(carrinho, cliente) -> None:
    com_x, _, _ = montar(GatewayPagamentoX())
    com_y, _, _ = montar(GatewayPagamentoY())

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


def test_camada_de_aplicacao_nao_importa_infraestrutura() -> None:
    """Fitness function: a decisao vira verificacao executavel.

    Equivale ao contrato `type = layers` de setup.cfg, e roda junto com
    os testes para quem ainda nao instalou o import-linter.

    Le o codigo-fonte com `ast` em vez de inspecionar o namespace do
    modulo ja carregado. A diferenca importa: `import
    mini_orion.infraestrutura.pagamentos` sem `from` nao cria nenhum
    nome novo no namespace e passaria despercebido por uma verificacao
    baseada em `vars()`.
    """
    import ast
    from pathlib import Path

    import mini_orion.aplicacao.checkout as modulo

    arvore = ast.parse(Path(modulo.__file__).read_text(encoding="utf-8"))

    importados: set[str] = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            importados.update(alias.name for alias in no.names)
        elif isinstance(no, ast.ImportFrom) and no.module:
            importados.add(no.module)

    proibidos = {"mini_orion.infraestrutura", "mini_orion.apresentacao"}
    violacoes = {
        i
        for i in importados
        if any(i == p or i.startswith(p + ".") for p in proibidos)
    }

    assert not violacoes, f"aplicacao voltou a depender de fora: {violacoes}"


def test_resultado_concentra_a_regra_de_contingencia() -> None:
    """A decisao de tentar outro provedor nao pode vazar para o checkout."""
    assert ResultadoCobranca.PROVEDOR_INDISPONIVEL.deve_tentar_outro_provedor
    assert ResultadoCobranca.ACIMA_DO_LIMITE.deve_tentar_outro_provedor
    assert not ResultadoCobranca.RECUSADA_PELO_EMISSOR.deve_tentar_outro_provedor
    assert not ResultadoCobranca.APROVADA.deve_tentar_outro_provedor


def test_pedido_de_cobranca_e_imutavel_e_nomeado() -> None:
    """Connascencia de posicao eliminada: campos por nome, objeto congelado."""
    from dataclasses import FrozenInstanceError

    from mini_orion.dominio import PedidoCobranca

    cobranca = PedidoCobranca(valor=380.0, cartao="4111111111")

    assert cobranca.parcelas == 1
    with pytest.raises(FrozenInstanceError):
        cobranca.valor = 1.0  # type: ignore[misc]

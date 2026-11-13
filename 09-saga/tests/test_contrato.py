"""O acordo entre `compra` e `pagamentos`, verificado dos dois lados.

Do lado do produtor: o contrato que o consumidor escreveu e rodado contra
o servidor, e a mudanca que quebra o acordo falha ANTES de ir ao ar.
Do lado do consumidor: o que cada leitor faz com um valor que nao conhece.
"""

import pytest

from mini_orion.montagem import montar_remoto
from mini_orion.nucleo.modelos import Carrinho, Cliente, ItemCarrinho
from mini_orion.pagamentos._provedores import GatewayPagamentoX, GatewayPagamentoXv2
from mini_orion.pagamentos._servidor import ServicoPagamentos
from mini_orion.pagamentos.api import ResultadoCobranca
from mini_orion.pagamentos.contrato import (
    RESULTADOS_V1,
    ResultadoDesconhecido,
    ler_ingenuo,
    leitor_tolerante,
)
from tests.verificador_contrato import verificar


def servidor_v1() -> ServicoPagamentos:
    return ServicoPagamentos(GatewayPagamentoX())


def acrescentando_campo(tratador):
    return lambda carga: {**tratador(carga), "provedor": "X"}


def renomeando_campo(tratador):
    def renomeado(carga):
        resposta = tratador(carga)
        return {"status": resposta["resultado"]}

    return renomeado


def removendo_campo(tratador):
    return lambda carga: {}


@pytest.fixture
def carrinho_alto() -> Carrinho:
    return Carrinho(itens=[ItemCarrinho(sku="TEC-09", preco_unitario=3000.0, quantidade=2)])


@pytest.fixture
def cliente() -> Cliente:
    return Cliente(nome="Maria", email="maria@exemplo.com", cartao="4111111111")


# --- lado do produtor -----------------------------------------------------


def test_o_produtor_atual_cumpre_o_contrato() -> None:
    assert verificar(servidor_v1().tratar_cobranca) == []


def test_acrescentar_um_campo_nao_quebra_o_acordo() -> None:
    assert verificar(acrescentando_campo(servidor_v1().tratar_cobranca)) == []


def test_renomear_um_campo_quebra_o_acordo() -> None:
    achados = verificar(renomeando_campo(servidor_v1().tratar_cobranca))

    assert any("campo 'resultado' ausente" in achado for achado in achados)


def test_remover_um_campo_quebra_o_acordo() -> None:
    achados = verificar(removendo_campo(servidor_v1().tratar_cobranca))

    assert len(achados) == 2  # as duas interacoes do contrato


def test_um_valor_novo_quebra_o_acordo_mesmo_sem_mudar_o_formato() -> None:
    servidor_v2 = ServicoPagamentos(GatewayPagamentoXv2())

    achados = verificar(servidor_v2.tratar_cobranca)

    assert achados == [
        "cobranca de valor alto, ainda dentro do limite do provedor: "
        "campo 'resultado' com valor 'em_analise' fora do acordo"
    ]


# --- lado do consumidor ---------------------------------------------------


def test_leitor_ingenuo_trata_o_valor_desconhecido_como_aprovada() -> None:
    assert ler_ingenuo({"resultado": "em_analise"}) is ResultadoCobranca.APROVADA


def test_leitor_ingenuo_emite_o_pedido_de_uma_cobranca_em_analise(
    carrinho_alto: Carrinho, cliente: Cliente
) -> None:
    cenario = montar_remoto(provedor=GatewayPagamentoXv2(), leitor=ler_ingenuo)
    cenario.rede.forcar(None)

    resultado = cenario.checkout.fechar_pedido(carrinho_alto, cliente)

    assert resultado == "confirmado"  # o pedido saiu sem cobranca aprovada
    assert cenario.pagamentos.cobrancas_aprovadas == []


def test_leitor_tolerante_trata_o_valor_desconhecido_como_falha(
    carrinho_alto: Carrinho, cliente: Cliente
) -> None:
    cenario = montar_remoto(
        provedor=GatewayPagamentoXv2(), leitor=leitor_tolerante(RESULTADOS_V1)
    )
    cenario.rede.forcar(None)

    resultado = cenario.checkout.fechar_pedido(carrinho_alto, cliente)

    assert resultado == "cobranca_indeterminada"


def test_leitor_tolerante_ignora_campo_extra_e_rejeita_campo_ausente() -> None:
    ler = leitor_tolerante(RESULTADOS_V1)

    assert ler({"resultado": "aprovada", "provedor": "X"}) is ResultadoCobranca.APROVADA
    with pytest.raises(ResultadoDesconhecido):
        ler({"status": "aprovada"})


def test_o_consumidor_na_v2_le_o_valor_novo(carrinho_alto: Carrinho, cliente: Cliente) -> None:
    cenario = montar_remoto(provedor=GatewayPagamentoXv2())  # leitor padrao: v2
    cenario.rede.forcar(None)

    resultado = cenario.checkout.fechar_pedido(carrinho_alto, cliente)

    assert resultado == "em_analise"

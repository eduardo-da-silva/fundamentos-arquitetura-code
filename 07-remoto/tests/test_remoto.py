"""Pagamentos do outro lado de uma rede simulada.

Cada teste mostra uma coisa que a chamada local nao tem. Os cenarios
exatos usam `forcar`; os estatisticos rodam muitas chamadas com semente
fixa e devolvem sempre o mesmo numero.
"""

import pytest

from mini_orion.montagem import CenarioRemoto, montar_remoto
from mini_orion.nucleo.modelos import Carrinho, Cliente, ItemCarrinho
from mini_orion.pagamentos.api import CobrancaIndeterminada, PedidoCobranca
from mini_orion.pagamentos.cliente import ClientePagamentos
from mini_orion.rede.api import (
    CAMPANHA,
    TIMEOUT_POR_CHAMADA,
    Falha,
    TimeoutDeRede,
)


def sem_chave() -> None:
    return None


@pytest.fixture
def carrinho() -> Carrinho:
    return Carrinho(itens=[ItemCarrinho(sku="TEC-01", preco_unitario=150.0, quantidade=2)])


@pytest.fixture
def cliente() -> Cliente:
    return Cliente(nome="Maria", email="maria@exemplo.com", cartao="4111111111")


def cobrancas_por_fechamento(
    cenario: CenarioRemoto, carrinho: Carrinho, cliente: Cliente, n: int
) -> list[int]:
    """Quantas vezes o provedor aprovou a cobranca em cada fechamento."""
    contagens = []
    for _ in range(n):
        antes = len(cenario.pagamentos.cobrancas_aprovadas)
        cenario.checkout.fechar_pedido(carrinho, cliente)
        contagens.append(len(cenario.pagamentos.cobrancas_aprovadas) - antes)
    return contagens


def test_chamada_remota_custa_tempo(carrinho: Carrinho, cliente: Cliente) -> None:
    cenario = montar_remoto()
    cenario.rede.forcar(None)

    resultado = cenario.checkout.fechar_pedido(carrinho, cliente)

    assert resultado == "confirmado"
    assert cenario.relogio.agora() > 0  # a chamada local custaria ~0


def test_pedido_perdido_na_ida_nao_executa_nada() -> None:
    cenario = montar_remoto()
    cenario.rede.forcar(Falha.PERDA_NA_IDA)
    cliente_pg = ClientePagamentos(cenario.rede, tentativas=1)

    with pytest.raises(CobrancaIndeterminada):
        cliente_pg.cobrar(PedidoCobranca(valor=100.0, cartao="4111111111"))

    assert cenario.pagamentos.cobrancas_aprovadas == []
    assert cenario.relogio.agora() == TIMEOUT_POR_CHAMADA


def test_resposta_perdida_na_volta_parece_igual_mas_cobrou() -> None:
    cenario = montar_remoto()
    cenario.rede.forcar(Falha.PERDA_NA_VOLTA)

    with pytest.raises(TimeoutDeRede):
        cenario.rede.chamar(
            "pagamentos",
            "cobrar",
            {"valor": 100.0, "cartao": "4111111111", "parcelas": 1, "chave": None},
            TIMEOUT_POR_CHAMADA,
        )

    # Mesmo TimeoutDeRede do teste anterior; efeito oposto.
    assert len(cenario.pagamentos.cobrancas_aprovadas) == 1


def test_repeticao_sem_chave_cobra_duas_vezes(carrinho: Carrinho, cliente: Cliente) -> None:
    cenario = montar_remoto(gerar_chave=sem_chave)
    cenario.rede.forcar(Falha.PERDA_NA_VOLTA, None)

    resultado = cenario.checkout.fechar_pedido(carrinho, cliente)

    assert resultado == "confirmado"
    assert len(cenario.pagamentos.cobrancas_aprovadas) == 2  # o cliente pagou em dobro


def test_repeticao_com_chave_cobra_uma_vez(carrinho: Carrinho, cliente: Cliente) -> None:
    cenario = montar_remoto()  # gera a chave por padrao
    cenario.rede.forcar(Falha.PERDA_NA_VOLTA, None)

    resultado = cenario.checkout.fechar_pedido(carrinho, cliente)

    assert resultado == "confirmado"
    assert len(cenario.pagamentos.cobrancas_aprovadas) == 1


def test_tentativas_esgotadas_nao_viram_recusa(carrinho: Carrinho, cliente: Cliente) -> None:
    cenario = montar_remoto()
    cenario.rede.forcar(Falha.PERDA_NA_IDA, Falha.PERDA_NA_VOLTA)

    resultado = cenario.checkout.fechar_pedido(carrinho, cliente)

    assert resultado == "cobranca_indeterminada"
    assert resultado != "recusada_pelo_emissor"
    assert len(cenario.pagamentos.cobrancas_aprovadas) == 1  # cobrou, e ninguem sabe


def test_em_campanha_a_repeticao_sem_chave_duplica_cerca_de_1_por_cento(
    carrinho: Carrinho, cliente: Cliente
) -> None:
    cenario = montar_remoto(CAMPANHA, semente=42, gerar_chave=sem_chave)

    contagens = cobrancas_por_fechamento(cenario, carrinho, cliente, n=2000)

    duplicadas = sum(1 for c in contagens if c > 1) / len(contagens)
    assert 0.005 <= duplicadas <= 0.020  # 2% de falha x 50% que perdem a resposta, mais as respostas lentas demais


def test_em_campanha_a_chave_zera_a_duplicacao(carrinho: Carrinho, cliente: Cliente) -> None:
    cenario = montar_remoto(CAMPANHA, semente=42)

    contagens = cobrancas_por_fechamento(cenario, carrinho, cliente, n=2000)

    assert max(contagens) == 1


def test_a_cauda_aparece_mas_o_p95_engana(carrinho: Carrinho, cliente: Cliente) -> None:
    cenario = montar_remoto(CAMPANHA, semente=42)
    duracoes = []
    for _ in range(2000):
        inicio = cenario.relogio.agora()
        cenario.checkout.fechar_pedido(carrinho, cliente)
        duracoes.append(cenario.relogio.agora() - inicio)
    duracoes.sort()

    p95 = duracoes[int(0.95 * len(duracoes)) - 1]
    na_cauda = sum(1 for d in duracoes if d >= TIMEOUT_POR_CHAMADA) / len(duracoes)

    assert p95 < 2.0  # dentro da meta de 2 s: o p95 nao acusa nada
    assert 0.010 <= na_cauda <= 0.030  # e ainda assim ~2% esperam um timeout inteiro

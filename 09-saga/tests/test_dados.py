"""O dado de `pagamentos` e de `pagamentos`.

A conciliacao roda sobre a copia local. Os testes mostram o que o
relatorio acusa sem a copia, o que ele acusa com ela e que o modulo nao
precisa de `compra` para rodar.
"""

import subprocess
import sys
from pathlib import Path

import pytest

from mini_orion.montagem import montar_remoto
from mini_orion.nucleo.modelos import Carrinho, Cliente, ItemCarrinho
from mini_orion.pagamentos._cobrancas import RegistroCobranca
from mini_orion.pagamentos.api import ResultadoCobranca
from mini_orion.pagamentos.conciliacao import Lancamento, conciliar
from mini_orion.rede.api import CAMPANHA, Falha

RAIZ = Path(__file__).resolve().parent.parent


@pytest.fixture
def carrinho() -> Carrinho:
    return Carrinho(itens=[ItemCarrinho(sku="TEC-01", preco_unitario=150.0, quantidade=2)])


@pytest.fixture
def cliente() -> Cliente:
    return Cliente(nome="Maria", email="maria@exemplo.com", cartao="4111111111")


def fechar(cenario, carrinho: Carrinho, cliente: Cliente, n: int) -> None:
    for _ in range(n):
        cenario.checkout.fechar_pedido(carrinho, cliente)


def test_cada_cobranca_deixa_uma_copia_local(carrinho: Carrinho, cliente: Cliente) -> None:
    cenario = montar_remoto()
    cenario.rede.forcar(None)

    cenario.checkout.fechar_pedido(carrinho, cliente)

    [registro] = cenario.pagamentos.repositorio.todos()
    assert registro.valor == 300.0
    assert registro.resultado is ResultadoCobranca.APROVADA


def test_a_copia_nao_guarda_o_cartao_inteiro(carrinho: Carrinho, cliente: Cliente) -> None:
    cenario = montar_remoto()
    cenario.rede.forcar(None)

    cenario.checkout.fechar_pedido(carrinho, cliente)

    [registro] = cenario.pagamentos.repositorio.todos()
    assert registro.cartao_final == "1111"
    assert cliente.cartao not in repr(registro)


def test_repeticao_com_chave_deixa_um_registro_so(carrinho: Carrinho, cliente: Cliente) -> None:
    cenario = montar_remoto()
    cenario.rede.forcar(Falha.PERDA_NA_VOLTA, None)

    cenario.checkout.fechar_pedido(carrinho, cliente)

    assert len(cenario.pagamentos.repositorio.todos()) == 1


def test_sem_a_copia_o_relatorio_fecha_com_diferenca(carrinho: Carrinho, cliente: Cliente) -> None:
    cenario = montar_remoto(CAMPANHA, semente=42, gravar_copia=False)
    fechar(cenario, carrinho, cliente, 50)

    relatorio = cenario.pagamentos.conciliar()

    assert not relatorio.fecha
    assert len(relatorio.so_no_provedor) == len(cenario.pagamentos.cobrancas_aprovadas)
    assert relatorio.conferem == []


def test_com_a_copia_o_relatorio_fecha(carrinho: Carrinho, cliente: Cliente) -> None:
    cenario = montar_remoto(CAMPANHA, semente=42)
    fechar(cenario, carrinho, cliente, 200)

    relatorio = cenario.pagamentos.conciliar()

    assert relatorio.fecha
    assert len(relatorio.conferem) == len(cenario.pagamentos.cobrancas_aprovadas) > 0


def test_a_copia_local_nao_enxerga_a_cobranca_sem_pedido(
    carrinho: Carrinho, cliente: Cliente
) -> None:
    cenario = montar_remoto(CAMPANHA, semente=42)
    resultados = [cenario.checkout.fechar_pedido(carrinho, cliente) for _ in range(2000)]

    relatorio = cenario.pagamentos.conciliar()

    sem_pedido = resultados.count("cobranca_indeterminada")
    assert sem_pedido == 2  # cobrados e sem pedido: o ensaio da Aula 16
    assert relatorio.fecha  # e o relatorio nao ve nenhum: so `compra` sabe que nao houve pedido


def test_a_conciliacao_aponta_o_que_so_o_provedor_conhece() -> None:
    registros = [RegistroCobranca("k-1", 100.0, "1111", ResultadoCobranca.APROVADA)]
    extrato = [Lancamento("k-1", 100.0), Lancamento("k-9", 40.0)]

    relatorio = conciliar(registros, extrato)

    assert relatorio.so_no_provedor == ["k-9"]
    assert relatorio.conferem == ["k-1"]


def test_a_conciliacao_aponta_valor_divergente_e_registro_sem_lancamento() -> None:
    registros = [
        RegistroCobranca("k-1", 100.0, "1111", ResultadoCobranca.APROVADA),
        RegistroCobranca("k-2", 80.0, "2222", ResultadoCobranca.APROVADA),
        RegistroCobranca("k-3", 70.0, "3333", ResultadoCobranca.RECUSADA_PELO_EMISSOR),
    ]
    extrato = [Lancamento("k-1", 90.0)]

    relatorio = conciliar(registros, extrato)

    assert relatorio.valor_divergente == ["k-1"]
    assert relatorio.so_no_orion == ["k-2"]  # k-3 foi recusada: nao e esperada no extrato


def test_a_conciliacao_roda_sem_carregar_compra() -> None:
    codigo = (
        "import sys;"
        "import mini_orion.pagamentos.conciliacao;"
        "assert not any(m.startswith('mini_orion.compra') for m in sys.modules)"
    )

    resultado = subprocess.run(
        [sys.executable, "-c", codigo],
        cwd=RAIZ,
        env={"PYTHONPATH": str(RAIZ)},
        capture_output=True,
        text=True,
    )

    assert resultado.returncode == 0, resultado.stderr

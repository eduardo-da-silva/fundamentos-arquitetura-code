"""Os numeros do ensaio da Aula 16, como contrato.

O texto da aula cita estes valores. Se o codigo mudar e eles mudarem,
estes testes falham, e a aula precisa ser revista junto.
"""

from ensaio import rodar

N = 2000
SEMENTE = 42


def test_ensaio_da_aula_repetir_sem_chave() -> None:
    r = rodar(N, SEMENTE, tentativas=2, com_chave=False)

    assert r.duplicadas == 22
    assert r.na_cauda == 39
    assert r.indeterminados == 2
    assert round(r.percentil(0.95) * 1000) == 214
    assert round(r.percentil(0.99) * 1000) == 1021


def test_politicas_da_aula() -> None:
    nao_repetir = rodar(N, SEMENTE, tentativas=1, com_chave=False)
    com_chave = rodar(N, SEMENTE, tentativas=2, com_chave=True)
    tres_tentativas = rodar(N, SEMENTE, tentativas=3, com_chave=True)

    assert (nao_repetir.indeterminados, nao_repetir.cobrados_sem_pedido) == (41, 24)
    assert (com_chave.indeterminados, com_chave.duplicadas) == (2, 0)
    assert (tres_tentativas.indeterminados, round(max(tres_tentativas.duracoes), 2)) == (1, 3.00)

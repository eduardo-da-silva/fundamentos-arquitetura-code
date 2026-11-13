"""O ensaio generico: as propriedades que o roteiro do projeto espera."""

import ensaio_generico as e


def test_com_chave_nenhum_pedido_e_executado_duas_vezes() -> None:
    assert e.rodar(2000, 42, 2, True)["duplicados"] == 0


def test_sem_chave_e_repetindo_ha_duplicados() -> None:
    assert e.rodar(2000, 42, 2, False)["duplicados"] > 0


def test_sem_repetir_nao_ha_duplicados() -> None:
    assert e.rodar(2000, 42, 1, False)["duplicados"] == 0


def test_mesma_semente_mesmo_resultado() -> None:
    assert e.rodar(500, 7, 2, False) == e.rodar(500, 7, 2, False)

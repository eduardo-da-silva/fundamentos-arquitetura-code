"""A conta da Aula 17, como contrato.

Os invariantes confirmam que o script usa o mesmo grafo das Aulas 7 e 12.
Os numeros por forma sao os que o texto da aula cita: se mudarem, a aula
precisa ser revista junto.
"""

import pytest

import quantum as q


def test_o_grafo_e_o_das_aulas_7_e_12() -> None:
    assert len(q.COMPONENTES) == 10
    assert len(q.ARESTAS) == 17
    ca = {c: sum(1 for _, b in q.ARESTAS if b == c) for c in q.COMPONENTES}
    ce = {c: sum(1 for a, _ in q.ARESTAS if a == c) for c in q.COMPONENTES}
    assert sum(ca.values()) == sum(ce.values()) == 17
    assert (ce["Checkout"], ca["Notificacoes"], ca["Catalogo"]) == (5, 4, 4)


def test_pagamentos_corta_ca_mais_ce_arestas() -> None:
    ca = sum(1 for _, b in q.ARESTAS if b == "Pagamentos")
    ce = sum(1 for a, _ in q.ARESTAS if a == "Pagamentos")
    assert (ca, ce) == (1, 1)
    assert len(q.arestas_remotas(q.forma_so_pagamentos())) == ca + ce


def test_os_oito_modulos_batem_com_a_aula_12() -> None:
    forma = q.forma_service_based()
    remotas = q.arestas_remotas(forma)
    internas = len(q.ARESTAS) - len(remotas)
    assert (internas, len(remotas)) == (2, 15)


@pytest.mark.parametrize(
    "nome, forma, banco, artefatos, remotas, diretas, quanta_sinc, quanta_fila",
    [
        ("monolito", q.forma_monolito, True, 1, 0, 0, 1, 1),
        ("so Pagamentos", q.forma_so_pagamentos, True, 2, 2, 1, 1, 1),
        ("service-based", q.forma_service_based, True, 8, 15, 4, 1, 1),
        ("service-based agrupado", q.forma_service_based_agrupado, True, 7, 14, 3, 1, 1),
        ("microsservicos", q.forma_microsservicos, False, 10, 17, 5, 1, 2),
    ],
)
def test_as_formas_da_aula(nome, forma, banco, artefatos, remotas, diretas, quanta_sinc, quanta_fila) -> None:
    linha = q.avaliar(nome, forma(), banco)

    assert linha.artefatos == artefatos
    assert linha.remotas == remotas
    assert linha.diretas == diretas
    assert linha.quanta_sincrono == quanta_sinc
    assert linha.quanta_com_fila == quanta_fila


def test_o_service_based_agrupado_da_aula() -> None:
    linha = q.avaliar("agrupado", q.forma_service_based_agrupado())
    assert q.artefatos_do_fechamento(q.forma_service_based_agrupado()) == 3
    assert round(100 * linha.p_falha, 1) == 5.9
    assert round(100 * linha.disponibilidade, 1) == 99.7
    assert round(linha.minutos) == 129


def test_probabilidade_e_disponibilidade_da_aula() -> None:
    assert round(q.p_ao_menos_uma_falha(1), 3) == 0.020
    assert round(q.p_ao_menos_uma_falha(4), 3) == 0.078
    assert round(q.p_ao_menos_uma_falha(5), 3) == 0.096
    assert [round(100 * q.disponibilidade_em_serie(n), 1) for n in (1, 2, 4, 6)] == [99.9, 99.8, 99.6, 99.4]
    assert [round((1 - q.disponibilidade_em_serie(n)) * q.MINUTOS_NO_MES) for n in (1, 2, 4, 6)] == [43, 86, 173, 259]


def test_dez_artefatos_ligados_por_chamada_sincrona_sao_um_quantum() -> None:
    assert q.quanta(q.forma_microsservicos()) == 1


def test_tornar_assincronas_as_arestas_de_notificacoes_separa_um_quantum() -> None:
    assincronas = q.notificacoes_assincronas()
    assert len(assincronas) == 4
    assert q.quanta(q.forma_microsservicos(), assincronas, banco_compartilhado=False) == 2


def test_banco_compartilhado_mantem_um_quantum_mesmo_sem_chamada_sincrona() -> None:
    # Nenhuma chamada e sincrona, mas todos dependem do mesmo banco.
    todas = set(q.ARESTAS)
    assert q.quanta(q.forma_microsservicos(), todas, banco_compartilhado=True) == 1
    # Com um banco por servico e nenhuma chamada sincrona, cada servico e um quantum.
    assert q.quanta(q.forma_microsservicos(), todas, banco_compartilhado=False) == 10


def test_fila_nao_separa_o_que_vive_no_mesmo_artefato() -> None:
    # Mesmo artefato, mesmo quantum: a fila entre dois componentes do monolito nao os separa.
    assert q.quanta(q.forma_monolito(), q.notificacoes_assincronas()) == 1


def test_particao_de_exemplo() -> None:
    forma = q.forma_de_particao(
        "Portal,Checkout,Pedidos|Catalogo,Promocoes|Pagamentos,Notificacoes,Logistica|Clientes,Integracoes"
    )
    linha = q.avaliar("exemplo", forma)
    assert (linha.artefatos, linha.remotas, linha.diretas) == (4, 11, 4)

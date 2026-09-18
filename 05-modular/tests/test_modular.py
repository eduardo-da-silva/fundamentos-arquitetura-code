"""Fitness function da estrutura modular por dominio.

Mesmo molde do `test_camadas.py` do checkpoint anterior: le o
codigo-fonte com `ast` (nao o namespace ja carregado) e verifica a
regra de dependencia entre os modulos de dominio.

A regra em uma frase: `compra` pode falar com as APIs publicas de
`pagamentos` e `notificacoes`, nunca com os internals `_*`; `pagamentos`
e `notificacoes` nao se conhecem nem conhecem `compra`.

Equivale aos contratos `independence` + `forbidden` de `setup.cfg` e
roda junto com os testes para quem ainda nao instalou o import-linter.
"""

import ast
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent / "mini_orion"

# A regra so faz sentido se os modulos existirem como pacotes.
# Verificamos isso primeiro para que os testes de import abaixo nao
# passem por vacuidade numa estrutura ainda em camadas.
MODULOS = ("nucleo", "compra", "pagamentos", "notificacoes")


def _imports(modulo: Path) -> set[str]:
    arvore = ast.parse(modulo.read_text(encoding="utf-8"))
    nomes: set[str] = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            nomes.update(a.name for a in no.names)
        elif isinstance(no, ast.ImportFrom) and no.module:
            nomes.add(no.module)
    return nomes


def _imports_do_pacote(nome: str) -> set[str]:
    pasta = RAIZ / nome
    assert pasta.is_dir(), f"modulo de dominio ausente: mini_orion.{nome}"
    total: set[str] = set()
    for arq in pasta.rglob("*.py"):
        total |= _imports(arq)
    return total


def _alcanca(achados: set[str], *prefixos: str) -> set[str]:
    return {
        i
        for i in achados
        if any(i == p or i.startswith(p + ".") for p in prefixos)
    }


def test_modulos_de_dominio_sao_pacotes() -> None:
    faltando = [m for m in MODULOS if not (RAIZ / m / "__init__.py").is_file()]
    assert not faltando, f"modulos ausentes: {faltando}"


def test_compra_nao_alcanca_internals() -> None:
    """`compra` depende das APIs publicas, nunca dos internals `_*`."""
    violacoes = _alcanca(
        _imports_do_pacote("compra"),
        "mini_orion.pagamentos._provedores",
        "mini_orion.notificacoes._fila",
    )
    assert not violacoes, f"compra alcancou internals de outro modulo: {violacoes}"


def test_pagamentos_nao_importa_compra_nem_notificacoes() -> None:
    violacoes = _alcanca(
        _imports_do_pacote("pagamentos"),
        "mini_orion.compra",
        "mini_orion.notificacoes",
    )
    assert not violacoes, f"pagamentos olhou para outro modulo: {violacoes}"


def test_notificacoes_nao_importa_compra_nem_pagamentos() -> None:
    violacoes = _alcanca(
        _imports_do_pacote("notificacoes"),
        "mini_orion.compra",
        "mini_orion.pagamentos",
    )
    assert not violacoes, f"notificacoes olhou para outro modulo: {violacoes}"

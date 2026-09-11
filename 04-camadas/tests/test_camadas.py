"""Fitness function da estrutura em camadas.

Le o codigo-fonte com `ast` (nao o namespace ja carregado) e verifica a
regra de dependencia: apresentacao > aplicacao > dominio, e o dominio
nao conhece infraestrutura.
"""

import ast
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent / "mini_orion"

# A regra de dependencia so faz sentido se as camadas existirem como
# pacotes. Verificamos isso primeiro para que os testes de import abaixo
# nao passem por vacuidade num pacote ainda plano.
CAMADAS = ("apresentacao", "aplicacao", "dominio", "infraestrutura")


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
    assert pasta.is_dir(), f"camada ausente: mini_orion.{nome}"
    total: set[str] = set()
    for arq in pasta.rglob("*.py"):
        total |= _imports(arq)
    return total


def test_todas_as_camadas_sao_pacotes() -> None:
    faltando = [c for c in CAMADAS if not (RAIZ / c / "__init__.py").is_file()]
    assert not faltando, f"camadas ausentes: {faltando}"


def test_dominio_nao_importa_aplicacao_nem_infra_nem_apresentacao() -> None:
    proibidos = {
        "mini_orion.aplicacao",
        "mini_orion.infraestrutura",
        "mini_orion.apresentacao",
    }
    achados = {i for i in _imports_do_pacote("dominio")
               if any(i == p or i.startswith(p + ".") for p in proibidos)}
    assert not achados, f"dominio olhou para fora: {achados}"


def test_aplicacao_nao_importa_infra_nem_apresentacao() -> None:
    proibidos = {"mini_orion.infraestrutura", "mini_orion.apresentacao"}
    achados = {i for i in _imports_do_pacote("aplicacao")
               if any(i == p or i.startswith(p + ".") for p in proibidos)}
    assert not achados, f"aplicacao olhou para fora: {achados}"

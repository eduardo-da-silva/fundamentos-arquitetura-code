"""Microkernel de regras de desconto: nucleo estavel, plugins removiveis."""

import ast
from pathlib import Path

from mini_orion.nucleo.modelos import Carrinho, ItemCarrinho
from mini_orion.promocoes.api import MotorPromocoes
from mini_orion.promocoes._regras.cupom_percentual import CupomPercentual
from mini_orion.promocoes._regras.frete_gratis_acima_de import FreteGratisAcimaDe


def _carrinho() -> Carrinho:
    return Carrinho(itens=[ItemCarrinho(sku="TEC-01", preco_unitario=200.0, quantidade=1)])


def test_composicao_de_dois_plugins() -> None:
    motor = MotorPromocoes()
    motor.registrar(CupomPercentual(0.10))
    motor.registrar(FreteGratisAcimaDe(150.0))
    descontos = motor.aplicar(_carrinho())
    assert len(descontos) == 2


def test_motor_funciona_sem_nenhum_plugin() -> None:
    assert MotorPromocoes().aplicar(_carrinho()) == []


def test_nucleo_nao_importa_plugins_concretos() -> None:
    fonte = (Path(__file__).resolve().parent.parent
             / "mini_orion" / "promocoes" / "api.py").read_text(encoding="utf-8")
    for no in ast.walk(ast.parse(fonte)):
        if isinstance(no, ast.ImportFrom) and no.module:
            assert "_regras" not in no.module, f"nucleo importou plugin: {no.module}"

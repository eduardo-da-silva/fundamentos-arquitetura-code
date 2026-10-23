"""Plugin: frete gratis quando o total passa de um piso.

Segundo plugin so para mostrar composicao: o motor soma este ao
`CupomPercentual` sem saber que nenhum dos dois existe em concreto.
"""

from dataclasses import dataclass

from mini_orion.nucleo.modelos import Carrinho
from mini_orion.promocoes.api import Desconto

FRETE_PADRAO = 25.0


@dataclass
class FreteGratisAcimaDe:
    piso: float

    def avalia(self, carrinho: Carrinho) -> Desconto | None:
        if carrinho.total < self.piso:
            return None
        return Desconto(origem="frete_gratis", valor=FRETE_PADRAO)

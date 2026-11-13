"""Plugin: cupom de desconto percentual sobre o total do carrinho.

Depende do nucleo (`api.Desconto`) para falar a lingua dele. O sentido
`_regras -> api` e permitido e esperado; o proibido e o inverso.
"""

from dataclasses import dataclass

from mini_orion.nucleo.modelos import Carrinho
from mini_orion.promocoes.api import Desconto


@dataclass
class CupomPercentual:
    fracao: float

    def avalia(self, carrinho: Carrinho) -> Desconto | None:
        if self.fracao <= 0:
            return None
        return Desconto(origem="cupom_percentual", valor=carrinho.total * self.fracao)

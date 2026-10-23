"""Nucleo: o *shared kernel* dos modulos de dominio.

So tipos de dados aqui -- `@dataclass` sem regra de negocio. `compra`,
`pagamentos` e `notificacoes` compartilham estes tipos sem depender uns
dos outros. As propriedades `subtotal` e `total` sao valor derivado dos
campos, nao decisao de negocio: nao ha politica de preco, imposto ou
desconto no nucleo. Regra que muda por decisao arquitetural mora no
modulo dono dela, nunca aqui.
"""

from dataclasses import dataclass, field


@dataclass
class ItemCarrinho:
    sku: str
    preco_unitario: float
    quantidade: int

    @property
    def subtotal(self) -> float:
        return self.preco_unitario * self.quantidade


@dataclass
class Carrinho:
    itens: list[ItemCarrinho] = field(default_factory=list)

    @property
    def total(self) -> float:
        return sum(item.subtotal for item in self.itens)


@dataclass
class Cliente:
    nome: str
    email: str
    cartao: str


@dataclass
class Pedido:
    numero: str
    cliente: Cliente
    total: float

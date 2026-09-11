"""Tipos do dominio, compartilhados pelos componentes."""

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

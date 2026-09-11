"""Camada de dominio: modelos e contratos, sem nenhuma dependencia externa.

O `__init__` re-exporta os nomes publicos de `modelos` e `contratos` para
que as camadas de cima continuem escrevendo `from mini_orion.dominio
import Carrinho, Gateway` — a reorganizacao em submodulos nao vaza para
quem consome o dominio.
"""

from mini_orion.dominio.contratos import (
    EventoNotificacao,
    Gateway,
    Notificador,
    PedidoCobranca,
    RepositorioDePedidos,
    ResultadoCobranca,
    evento_de_confirmacao,
)
from mini_orion.dominio.modelos import (
    Carrinho,
    Cliente,
    ItemCarrinho,
    Pedido,
)

__all__ = [
    "Carrinho",
    "Cliente",
    "ItemCarrinho",
    "Pedido",
    "EventoNotificacao",
    "Gateway",
    "Notificador",
    "PedidoCobranca",
    "RepositorioDePedidos",
    "ResultadoCobranca",
    "evento_de_confirmacao",
]

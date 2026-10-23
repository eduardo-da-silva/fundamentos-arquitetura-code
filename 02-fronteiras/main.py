from mini_orion.dominio import Cliente, Carrinho, ItemCarrinho
from mini_orion.checkout import ServicoCheckout
from mini_orion.notificacoes import FilaNotificacoes
from mini_orion.pagamentos import GatewayPagamentoX
from mini_orion.pedidos import RepositorioPedidos


cliente1 = Cliente(nome="Eduardo", email="eduardo.silva@ifc.edu.br", cartao="4111111111111")
carrinho_cliente1 = Carrinho(
    itens=[
        ItemCarrinho(sku="1", preco_unitario=100.0, quantidade=2),
        ItemCarrinho(sku="2", preco_unitario=150.0, quantidade=3)
    ]
)

meu_gateway_pagamento = GatewayPagamentoX()
meus_pedidos = RepositorioPedidos()
minha_fila = FilaNotificacoes()

checkout = ServicoCheckout(
    gateway=meu_gateway_pagamento, 
    pedidos=meus_pedidos,
    notificador=minha_fila
)

resultado = checkout.fechar_pedido(carrinho=carrinho_cliente1, cliente=cliente1)
print(resultado)
from mini_orion.checkout import Cliente, Carrinho, ItemCarrinho, ServicoCheckout

cliente1 = Cliente(nome="Eduardo", email="eduardo.silva@ifc.edu.br", cartao="444444444")
carrinho_cliente1 = Carrinho(
    itens = [
        ItemCarrinho(sku="1", preco_unitario=100.0, quantidade=2),
        ItemCarrinho(sku="2", preco_unitario=150.0, quantidade=3)
    ]
)

print("Valor total do carrinho")
total = sum(item.subtotal for item in carrinho_cliente1.itens)
print(total)
checkout = ServicoCheckout()
resultado = checkout.fechar_pedido(carrinho_cliente1, cliente1)
print(resultado)
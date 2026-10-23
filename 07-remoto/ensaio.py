"""Ensaio de campanha da Aula 16: reproduz as tabelas da aula.

Uso, a partir desta pasta:

    python ensaio.py                      # 2000 fechamentos, semente 42
    python ensaio.py --fechamentos 10000  # mais fechamentos
    python ensaio.py --semente 7          # outra rodada
    python ensaio.py --varrer             # a mesma rodada em 10 sementes

Nada aqui mede o Orion. O ensaio executa o codigo real de `compra` e
`pagamentos` sobre uma rede simulada cujos parametros sao as hipoteses
de trabalho da aula (ver `mini_orion/rede/api.py`). Para ver o que
muda quando as hipoteses mudam, altere `CAMPANHA` la e rode de novo.
"""

import argparse
from dataclasses import dataclass

from mini_orion.montagem import CenarioRemoto, montar_remoto
from mini_orion.nucleo.modelos import Carrinho, ChaveIdempotencia, Cliente, ItemCarrinho
from mini_orion.rede.api import CAMPANHA, TIMEOUT_POR_CHAMADA

CLIENTE = Cliente(nome="Maria", email="maria@exemplo.com", cartao="4111111111")


@dataclass
class Resultado:
    duracoes: list[float]
    confirmados: int
    indeterminados: int
    duplicadas: int
    cobrados_sem_pedido: int

    def percentil(self, p: float) -> float:
        """Percentil por posicao: o menor valor que cobre p% das rodadas."""
        ordenadas = sorted(self.duracoes)
        return ordenadas[int(p * len(ordenadas)) - 1]

    @property
    def na_cauda(self) -> int:
        """Fechamentos que esperaram pelo menos um timeout inteiro."""
        return sum(1 for d in self.duracoes if d >= TIMEOUT_POR_CHAMADA)


def carrinho() -> Carrinho:
    return Carrinho(itens=[ItemCarrinho(sku="TEC-01", preco_unitario=150.0, quantidade=2)])


def rodar(n: int, semente: int, tentativas: int, com_chave: bool) -> Resultado:
    gerar_chave = ChaveIdempotencia.nova if com_chave else (lambda: None)
    cenario: CenarioRemoto = montar_remoto(
        CAMPANHA, semente, tentativas=tentativas, gerar_chave=gerar_chave
    )
    duracoes: list[float] = []
    confirmados = indeterminados = duplicadas = cobrados_sem_pedido = 0
    for _ in range(n):
        antes = len(cenario.pagamentos.cobrancas_aprovadas)
        inicio = cenario.relogio.agora()
        desfecho = cenario.checkout.fechar_pedido(carrinho(), CLIENTE)
        duracoes.append(cenario.relogio.agora() - inicio)
        cobrancas = len(cenario.pagamentos.cobrancas_aprovadas) - antes
        confirmados += desfecho == "confirmado"
        indeterminados += desfecho == "cobranca_indeterminada"
        duplicadas += cobrancas > 1
        cobrados_sem_pedido += cobrancas >= 1 and desfecho != "confirmado"
    return Resultado(duracoes, confirmados, indeterminados, duplicadas, cobrados_sem_pedido)


def pct(parte: int, total: int) -> str:
    return f"{100 * parte / total:.2f}%".replace(".", ",")


def imprimir_painel(r: Resultado, n: int) -> None:
    print(f"\n== O ensaio: {n} fechamentos, repetir uma vez, SEM chave ==")
    print(f"  mediana                         {r.percentil(0.50) * 1000:6.0f} ms")
    print(f"  percentil 95                    {r.percentil(0.95) * 1000:6.0f} ms   (meta: 2000 ms)")
    print(f"  percentil 99                    {r.percentil(0.99) * 1000:6.0f} ms")
    print(f"  esperaram um timeout inteiro    {r.na_cauda:6d}      ({pct(r.na_cauda, n)})")
    print(f"  cobrados duas vezes             {r.duplicadas:6d}      ({pct(r.duplicadas, n)})")
    print(f"  terminaram em 'nao sei'         {r.indeterminados:6d}")


def imprimir_politicas(n: int, semente: int) -> None:
    politicas = [
        ("nao repetir (1 tentativa)", 1, False),
        ("repetir sem chave (2)", 2, False),
        ("repetir com chave (2)", 2, True),
        ("repetir com chave (3)", 3, True),
    ]
    print(f"\n== Tres politicas de repeticao, {n} fechamentos, semente {semente} ==")
    print(f"  {'politica':28} {'sem resposta':>13} {'duplicadas':>11} {'cobrado s/ pedido':>18} {'pior':>7}")
    for nome, tentativas, com_chave in politicas:
        r = rodar(n, semente, tentativas, com_chave)
        print(
            f"  {nome:28} {r.indeterminados:13d} {r.duplicadas:11d} "
            f"{r.cobrados_sem_pedido:18d} {max(r.duracoes):6.2f}s"
        )


def imprimir_varredura(n: int) -> None:
    print(f"\n== Mesma politica (repetir sem chave), {n} fechamentos, 10 sementes ==")
    print(f"  {'semente':>8} {'p95 (ms)':>9} {'timeout inteiro':>16} {'duplicadas':>11}")
    for semente in range(1, 11):
        r = rodar(n, semente, tentativas=2, com_chave=False)
        print(
            f"  {semente:8d} {r.percentil(0.95) * 1000:9.0f} "
            f"{pct(r.na_cauda, n):>16} {pct(r.duplicadas, n):>11}"
        )


def main() -> None:
    analise = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    analise.add_argument("--fechamentos", type=int, default=2000)
    analise.add_argument("--semente", type=int, default=42)
    analise.add_argument("--varrer", action="store_true", help="repete em 10 sementes")
    args = analise.parse_args()

    imprimir_painel(rodar(args.fechamentos, args.semente, 2, False), args.fechamentos)
    imprimir_politicas(args.fechamentos, args.semente)
    if args.varrer:
        imprimir_varredura(args.fechamentos)


if __name__ == "__main__":
    main()

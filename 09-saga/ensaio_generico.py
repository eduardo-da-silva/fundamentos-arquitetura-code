"""Ensaio generico: uma operacao com efeito colateral atras de uma rede simulada.

Uso, a partir desta pasta:

    python ensaio_generico.py
    python ensaio_generico.py --pedidos 10000 --semente 7

E a versao do `ensaio.py` que nao conhece o Orion: nao ha `compra` nem
`pagamentos`, so uma operacao que, cada vez que o servidor a executa,
produz um efeito que nao pode se repetir (uma reserva, um envio, uma
cobranca). Quem aplica o ensaio a um cenario proprio troca os nomes e os
parametros nas constantes abaixo, sem editar o resto.

A rede e a mesma do `ensaio.py` (`RedeSimulada`): sem socket e sem espera
real. Os valores abaixo sao hipoteses, nao medicoes.
"""

import argparse

from mini_orion.rede._simulada import RedeSimulada, RelogioSimulado
from mini_orion.rede.api import ParametrosRede, TimeoutDeRede

# --- O que voce troca para o seu cenario ---------------------------------
OPERACAO = "reservar assento"  # so aparece nos titulos
PARAMETROS = ParametrosRede(
    latencia_mediana=0.050,  # segundos: a metade das chamadas responde antes disto
    latencia_p99=0.800,  # segundos: 99% das chamadas respondem antes disto
    taxa_falha=0.01,  # fracao das chamadas que se perde (metade na ida, metade na volta)
)
TIMEOUT = 1.0  # segundos que quem chama espera por uma resposta
# --------------------------------------------------------------------------


class Servidor:
    """Quem executa a operacao. Com chave, guarda a resposta e nao repete o efeito."""

    def __init__(self) -> None:
        self.efeitos_por_pedido: dict[str, int] = {}
        self._respostas: dict[str, dict[str, object]] = {}

    def tratar(self, carga: dict[str, object]) -> dict[str, object]:
        pedido = str(carga["pedido"])
        chave = carga.get("chave")
        if chave is not None and chave in self._respostas:
            return self._respostas[str(chave)]
        self.efeitos_por_pedido[pedido] = self.efeitos_por_pedido.get(pedido, 0) + 1
        resposta: dict[str, object] = {"ok": True}
        if chave is not None:
            self._respostas[str(chave)] = resposta
        return resposta


def rodar(pedidos: int, semente: int, tentativas: int, com_chave: bool) -> dict[str, float]:
    relogio = RelogioSimulado()
    rede = RedeSimulada(relogio, PARAMETROS, semente)
    servidor = Servidor()
    rede.registrar("servico", "executar", servidor.tratar)

    sem_resposta = 0
    duracoes: list[float] = []
    for n in range(pedidos):
        carga: dict[str, object] = {"pedido": f"p{n}"}
        if com_chave:
            carga["chave"] = f"chave-{n}"
        inicio = relogio.agora()
        respondeu = False
        for _ in range(tentativas):
            try:
                rede.chamar("servico", "executar", carga, TIMEOUT)
                respondeu = True
                break
            except TimeoutDeRede:
                continue
        duracoes.append(relogio.agora() - inicio)
        sem_resposta += not respondeu

    efeitos = servidor.efeitos_por_pedido
    duplicados = sum(1 for v in efeitos.values() if v > 1)
    feitos_sem_resposta = sum(
        1 for n in range(pedidos) if efeitos.get(f"p{n}", 0) >= 1
    ) - (pedidos - sem_resposta)
    duracoes.sort()
    return {
        "sem_resposta": sem_resposta,
        "duplicados": duplicados,
        "feitos_sem_resposta": feitos_sem_resposta,
        "p95": duracoes[int(0.95 * pedidos) - 1],
        "pior": duracoes[-1],
    }


def main() -> None:
    analise = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    analise.add_argument("--pedidos", type=int, default=2000)
    analise.add_argument("--semente", type=int, default=42)
    args = analise.parse_args()

    politicas = [
        ("nao repetir (1 tentativa)", 1, False),
        ("repetir sem chave (2)", 2, False),
        ("repetir com chave (2)", 2, True),
        ("repetir com chave (3)", 3, True),
    ]
    print(f"\n== {OPERACAO}: {args.pedidos} pedidos, semente {args.semente} ==")
    print(f"  {'politica':28} {'sem resposta':>13} {'duplicados':>11} {'feito s/ resposta':>18} {'p95':>7} {'pior':>7}")
    for nome, tentativas, com_chave in politicas:
        r = rodar(args.pedidos, args.semente, tentativas, com_chave)
        print(
            f"  {nome:28} {r['sem_resposta']:13.0f} {r['duplicados']:11.0f} "
            f"{r['feitos_sem_resposta']:18.0f} {r['p95']:6.2f}s {r['pior']:6.2f}s"
        )


if __name__ == "__main__":
    main()

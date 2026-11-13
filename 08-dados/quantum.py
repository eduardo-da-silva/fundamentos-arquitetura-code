"""O quantum do Orion, calculado do grafo: a conta da Aula 17.

Uso, a partir desta pasta:

    python quantum.py                           # as quatro formas da aula
    python quantum.py --notificacoes-assincronas  # arestas para Notificacoes via fila
    python quantum.py --banco-unico             # todas as formas atras de um banco so
    python quantum.py --particao "Portal,Checkout|Catalogo|Pagamentos"
                                                # uma forma sua; o que sobrar fica junto

Este script nao usa o Mini-Orion: opera sobre o grafo do Marketplace Orion
inteiro, os dez componentes e as 17 arestas das Aulas 7 e 12 (`A -> B`
significa que A depende de B). As taxas de falha e de disponibilidade sao
as hipoteses de trabalho das Aulas 16 e 17, nao medicoes.
"""

import argparse
from dataclasses import dataclass

# `A -> B`: A depende de B. As 17 arestas do grafo das Aulas 7 e 12.
ARESTAS: list[tuple[str, str]] = [
    ("Portal", "Catalogo"),
    ("Portal", "Checkout"),
    ("Portal", "Pedidos"),
    ("Portal", "Clientes"),
    ("Checkout", "Catalogo"),
    ("Checkout", "Clientes"),
    ("Checkout", "Promocoes"),
    ("Checkout", "Pagamentos"),
    ("Checkout", "Pedidos"),
    ("Promocoes", "Catalogo"),
    ("Pedidos", "Notificacoes"),
    ("Pedidos", "Logistica"),
    ("Pagamentos", "Notificacoes"),
    ("Logistica", "Notificacoes"),
    ("Integracoes", "Catalogo"),
    ("Integracoes", "Pedidos"),
    ("Integracoes", "Notificacoes"),
]

COMPONENTES = sorted({c for aresta in ARESTAS for c in aresta})

# Dois componentes que a conta trata de modo especial. Quem aplicar o script a
# outro grafo troca estes dois nomes, alem de ARESTAS e MODULOS.
ORIGEM_DO_FLUXO = "Checkout"  # o componente cujas chamadas formam o caminho do fluxo medido
DESTINO_DA_FILA = "Notificacoes"  # quem recebe as arestas que podem passar por fila

# Os oito modulos de dominio da Aula 12.
MODULOS: dict[str, list[str]] = {
    "Borda": ["Portal"],
    "Vitrine": ["Catalogo", "Promocoes"],
    "Compra": ["Checkout", "Pedidos"],
    "Financeiro": ["Pagamentos"],
    "Distribuicao": ["Logistica"],
    "Comunicacao": ["Notificacoes"],
    "Identidade": ["Clientes"],
    "Integracao": ["Integracoes"],
}

# Hipoteses de trabalho (Aulas 16 e 17): nao sao medicoes do Orion.
TAXA_DE_FALHA = 0.02  # por chamada remota, em campanha
DISPONIBILIDADE = 0.999  # mensal, de cada artefato implantavel
MINUTOS_NO_MES = 30 * 24 * 60

Forma = dict[str, str]  # componente -> artefato implantavel em que vive


def forma_monolito() -> Forma:
    return {c: "orion" for c in COMPONENTES}


def forma_so_pagamentos() -> Forma:
    return {c: ("pagamentos" if c == "Pagamentos" else "orion") for c in COMPONENTES}


def forma_service_based() -> Forma:
    return {c: modulo for modulo, itens in MODULOS.items() for c in itens}


def forma_service_based_agrupado() -> Forma:
    """Sete servicos: como o service-based dos oito dominios, mas `Pagamentos` fica
    junto de `Compra` (`Checkout` e `Pedidos`), e a cobranca vira transacao local."""
    forma = forma_service_based()
    forma["Pagamentos"] = forma["Checkout"]
    return forma


def forma_microsservicos() -> Forma:
    return {c: c for c in COMPONENTES}


def forma_de_particao(texto: str) -> Forma:
    """`A,B|C|D,E` vira tres artefatos; o que nao for citado fica junto."""
    forma: Forma = {}
    for n, grupo in enumerate(texto.split("|")):
        for componente in grupo.split(","):
            nome = componente.strip()
            if nome not in COMPONENTES:
                raise SystemExit(f"componente desconhecido: {nome!r}")
            forma[nome] = f"artefato-{n + 1}"
    for c in COMPONENTES:
        forma.setdefault(c, "resto")
    return forma


def arestas_remotas(forma: Forma) -> list[tuple[str, str]]:
    """Arestas cujas pontas vivem em artefatos diferentes."""
    return [(a, b) for a, b in ARESTAS if forma[a] != forma[b]]


def chamadas_diretas_de(forma: Forma, origem: str = ORIGEM_DO_FLUXO) -> int:
    """Chamadas remotas que `origem` faz diretamente a outros componentes."""
    return sum(1 for a, b in arestas_remotas(forma) if a == origem)


def artefatos_do_fechamento(forma: Forma, origem: str = ORIGEM_DO_FLUXO) -> int:
    """Artefatos que um fechamento de compra toca: o do `Checkout` e os que ele chama."""
    tocados = {forma[origem]} | {forma[b] for a, b in ARESTAS if a == origem}
    return len(tocados)


def quanta(
    forma: Forma,
    assincronas: set[tuple[str, str]] | None = None,
    banco_compartilhado: bool = True,
) -> int:
    """Conta os quanta: componentes ligados por artefato comum, por chamada sincrona
    OU por um banco compartilhado.

    Mesmo artefato: nao se implantam separados. Chamada sincrona: a disponibilidade
    e a escala de quem chama dependem de quem e chamado. Banco compartilhado: todos
    os componentes atras dele dependem do mesmo ponto de acoplamento, mesmo que
    nenhum chame o outro.
    """
    assincronas = assincronas or set()
    pai = {c: c for c in COMPONENTES}

    def raiz(c: str) -> str:
        while pai[c] != c:
            pai[c] = pai[pai[c]]
            c = pai[c]
        return c

    ligacoes = [(a, b) for a in COMPONENTES for b in COMPONENTES if forma[a] == forma[b]]
    ligacoes += [aresta for aresta in ARESTAS if aresta not in assincronas]
    if banco_compartilhado:
        ligacoes += [(COMPONENTES[0], c) for c in COMPONENTES[1:]]
    for a, b in ligacoes:
        pai[raiz(a)] = raiz(b)
    return len({raiz(c) for c in COMPONENTES})


def notificacoes_assincronas() -> set[tuple[str, str]]:
    """As arestas que chegam em `DESTINO_DA_FILA`, trocadas por fila."""
    return {(a, b) for a, b in ARESTAS if b == DESTINO_DA_FILA}


def p_ao_menos_uma_falha(chamadas: int, taxa: float = TAXA_DE_FALHA) -> float:
    return 1 - (1 - taxa) ** chamadas


def disponibilidade_em_serie(artefatos: int, base: float = DISPONIBILIDADE) -> float:
    return base**artefatos


@dataclass
class Linha:
    nome: str
    artefatos: int
    remotas: int
    diretas: int
    p_falha: float
    disponibilidade: float
    minutos: float
    quanta_sincrono: int
    quanta_com_fila: int


def avaliar(nome: str, forma: Forma, banco_compartilhado: bool = True) -> Linha:
    tocados = artefatos_do_fechamento(forma)
    diretas = chamadas_diretas_de(forma)
    disp = disponibilidade_em_serie(tocados)
    return Linha(
        nome=nome,
        artefatos=len(set(forma.values())),
        remotas=len(arestas_remotas(forma)),
        diretas=diretas,
        p_falha=p_ao_menos_uma_falha(diretas),
        disponibilidade=disp,
        minutos=(1 - disp) * MINUTOS_NO_MES,
        quanta_sincrono=quanta(forma, banco_compartilhado=banco_compartilhado),
        quanta_com_fila=quanta(forma, notificacoes_assincronas(), banco_compartilhado),
    )


def pct(x: float) -> str:
    return f"{100 * x:.1f}%".replace(".", ",")


def imprimir(linhas: list[Linha], so_com_fila: bool) -> None:
    print(f"Grafo: {len(COMPONENTES)} componentes, {len(ARESTAS)} arestas.")
    print(f"Hipoteses: falha de {pct(TAXA_DE_FALHA)} por chamada remota; "
          f"{pct(DISPONIBILIDADE)} de disponibilidade por artefato.\n")
    col = "quanta (fila)" if so_com_fila else "quanta (sinc.)"
    print(f"{'forma':26}{'artefatos':>10}{'arestas':>9}{'chamadas':>10}{'P(falha)':>10}"
          f"{'disponib.':>11}{'min/mes':>9}{col:>16}")
    for x in linhas:
        q = x.quanta_com_fila if so_com_fila else x.quanta_sincrono
        print(f"{x.nome:26}{x.artefatos:10d}{x.remotas:9d}{x.diretas:10d}{pct(x.p_falha):>10}"
              f"{pct(x.disponibilidade):>11}{x.minutos:9.0f}{q:16d}")
    print("\narestas = arestas remotas; chamadas = chamadas remotas diretas do Checkout;")
    print("disponib. e min/mes = artefatos tocados por um fechamento, em serie.")


def main() -> None:
    analise = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    analise.add_argument("--notificacoes-assincronas", action="store_true",
                         help="troca por fila as arestas que chegam em Notificacoes")
    analise.add_argument("--banco-unico", action="store_true",
                         help="todas as formas atras de um banco so (os microsservicos, "
                              "por padrao, tem um banco por servico)")
    analise.add_argument("--particao", help='forma propria, ex.: "Portal,Checkout|Catalogo"')
    args = analise.parse_args()

    # (nome, forma, banco compartilhado?): so os microsservicos separam o dado.
    formas = [
        ("monolito modular", forma_monolito(), True),
        ("so Pagamentos", forma_so_pagamentos(), True),
        ("service-based (8 dominios)", forma_service_based(), True),
        ("service-based agrupado (7)", forma_service_based_agrupado(), True),
        ("microsservicos (10)", forma_microsservicos(), args.banco_unico),
    ]
    if args.particao:
        formas.append(("sua particao", forma_de_particao(args.particao), True))
    imprimir([avaliar(n, f, banco or args.banco_unico) for n, f, banco in formas],
             args.notificacoes_assincronas)


if __name__ == "__main__":
    main()

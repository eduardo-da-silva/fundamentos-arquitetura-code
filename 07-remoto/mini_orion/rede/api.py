"""API publica do modulo Rede -- o que existe entre dois processos.

Dentro de um processo, chamar outro modulo e chamar uma funcao: devolve,
ou levanta uma excecao na hora. Entre processos, ha um terceiro
resultado que a chamada local nao tem: nao saber. O pedido pode nao ter
chegado, ou ter chegado e a resposta ter se perdido. Para quem chama, os
dois casos aparecem do mesmo jeito -- `TimeoutDeRede` -- e e a diferenca
entre eles que a Aula 16 mede.

A rede aqui e SIMULADA em processo: sem socket, sem thread, sem espera
real. Ela reproduz a forma do problema -- latencia que nao e zero, falha
que nao e excecao local --, nao a fisica da rede. Os valores sao as
hipoteses de trabalho da Aula 16, nao medicoes do Orion.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Protocol

Carga = dict[str, object]
Tratador = Callable[[Carga], Carga]


class TimeoutDeRede(Exception):
    """O chamador esperou o tempo combinado e nao obteve resposta."""


class DestinoDesconhecido(Exception):
    """Ninguem esta registrado para atender esta operacao."""


class Falha(Enum):
    """Duas falhas diferentes que, para o chamador, sao a mesma."""

    PERDA_NA_IDA = "perda_na_ida"  # o pedido nao chegou: nada foi feito
    PERDA_NA_VOLTA = "perda_na_volta"  # chegou e foi feito: a resposta se perdeu


@dataclass(frozen=True)
class ParametrosRede:
    latencia_mediana: float
    latencia_p99: float
    taxa_falha: float
    proporcao_perda_na_volta: float = 0.5


# Hipoteses de trabalho da Aula 16. A latencia e a mesma nos dois cenarios:
# o que muda em campanha e a taxa de falha.
CAMPANHA = ParametrosRede(latencia_mediana=0.020, latencia_p99=0.400, taxa_falha=0.02)
NORMAL = ParametrosRede(latencia_mediana=0.020, latencia_p99=0.400, taxa_falha=0.002)

TIMEOUT_POR_CHAMADA = 1.0
TIMEOUT_DO_FECHAMENTO = 3.0


class Relogio(Protocol):
    def agora(self) -> float: ...


class Transporte(Protocol):
    def chamar(
        self, destino: str, operacao: str, carga: Carga, timeout: float
    ) -> Carga: ...


class Registro(Protocol):
    def registrar(self, destino: str, operacao: str, tratador: Tratador) -> None: ...

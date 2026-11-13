"""Observabilidade: o registro de eventos e o que ele permite reconstruir.

Cada modulo guarda o seu proprio registro, como guardariam dois servicos
com dois arquivos de log. O que os liga e o identificador de correlacao:
um valor gerado na entrada do fechamento e carregado em toda chamada.
Sem ele, os dois registros existem e ninguem sabe quais linhas contam a
mesma historia.

Este modulo nao conhece nenhum modulo de dominio: contrato `forbidden`
em `setup.cfg`.
"""

from dataclasses import dataclass
from itertools import count
from typing import Callable

# Ordem global dos eventos dentro do processo simulado. Num sistema real
# cada servico teria o seu relogio, e a ordem entre servicos seria uma
# inferencia; aqui ela e exata, e a aula diz que isso e uma facilidade.
_SEQUENCIA = count(1)


@dataclass(frozen=True)
class Evento:
    sequencia: int
    instante: float
    origem: str
    correlacao: str | None
    mensagem: str


class Registro:
    def __init__(self, origem: str, agora: Callable[[], float]) -> None:
        self._origem = origem
        self._agora = agora
        self.eventos: list[Evento] = []

    def registrar(self, mensagem: str, correlacao: str | None = None) -> None:
        self.eventos.append(
            Evento(next(_SEQUENCIA), self._agora(), self._origem, correlacao, mensagem)
        )


def reconstruir(correlacao: str, *registros: Registro) -> list[Evento]:
    """Junta, em ordem, os eventos de todos os registros que levam o identificador."""
    todos = [e for r in registros for e in r.eventos if e.correlacao == correlacao]
    return sorted(todos, key=lambda e: (e.instante, e.sequencia))

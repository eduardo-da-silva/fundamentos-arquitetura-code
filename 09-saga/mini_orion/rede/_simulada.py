"""Interno do modulo Rede -- o transporte simulado.

Determinismo: o sorteio usa semente fixa e o relogio e injetado. Nenhum
teste dorme, e nenhum teste e intermitente. Quando um teste precisa de
uma falha exata, usa `forcar`; quando precisa de uma estatistica, roda
muitas chamadas com a mesma semente e obtem sempre o mesmo numero.
"""

import math
import random
from collections import deque

from mini_orion.rede.api import (
    Carga,
    DestinoDesconhecido,
    Falha,
    ParametrosRede,
    TimeoutDeRede,
    Tratador,
)

_Z_P99 = 2.3263  # quantil 99% da normal padrao


class RelogioSimulado:
    """Tempo que so anda quando alguem o faz andar."""

    def __init__(self) -> None:
        self._agora = 0.0

    def agora(self) -> float:
        return self._agora

    def avancar(self, segundos: float) -> None:
        self._agora += segundos


class RedeSimulada:
    def __init__(
        self, relogio: RelogioSimulado, parametros: ParametrosRede, semente: int = 42
    ) -> None:
        self._relogio = relogio
        self._parametros = parametros
        self._sorteio = random.Random(semente)
        self._tratadores: dict[tuple[str, str], Tratador] = {}
        self._forcadas: deque[Falha | None] = deque()
        self.chamadas = 0

    def registrar(self, destino: str, operacao: str, tratador: Tratador) -> None:
        self._tratadores[(destino, operacao)] = tratador

    def forcar(self, *desfechos: Falha | None) -> None:
        """Define o desfecho das proximas chamadas; None significa sem falha."""
        self._forcadas.extend(desfechos)

    def chamar(
        self, destino: str, operacao: str, carga: Carga, timeout: float
    ) -> Carga:
        tratador = self._tratadores.get((destino, operacao))
        if tratador is None:
            raise DestinoDesconhecido(f"{destino}/{operacao}")
        self.chamadas += 1
        falha = self._proximo_desfecho()
        latencia = self._sortear_latencia()
        if falha is Falha.PERDA_NA_IDA:
            self._esgotar(timeout)
        resposta = tratador(carga)  # o servidor fez o trabalho
        if falha is Falha.PERDA_NA_VOLTA or latencia > timeout:
            self._esgotar(timeout)
        self._relogio.avancar(latencia)
        return resposta

    def _esgotar(self, timeout: float) -> None:
        self._relogio.avancar(timeout)
        raise TimeoutDeRede(f"sem resposta em {timeout:.1f}s")

    def _proximo_desfecho(self) -> Falha | None:
        if self._forcadas:
            return self._forcadas.popleft()
        if self._sorteio.random() >= self._parametros.taxa_falha:
            return None
        if self._sorteio.random() < self._parametros.proporcao_perda_na_volta:
            return Falha.PERDA_NA_VOLTA
        return Falha.PERDA_NA_IDA

    def _sortear_latencia(self) -> float:
        """Lognormal com a mediana e o p99 dos parametros."""
        mu = math.log(self._parametros.latencia_mediana)
        sigma = math.log(self._parametros.latencia_p99 / self._parametros.latencia_mediana) / _Z_P99
        return self._sorteio.lognormvariate(mu, sigma)

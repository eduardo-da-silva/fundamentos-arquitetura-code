"""Conciliacao: cruza o que o Orion registrou com o que o provedor reporta.

Roda so com dados de `pagamentos`. A versao anterior cruzava tambem com a
tabela de pedidos; aqui o modulo nao importa `compra`, e o contrato
`conciliacao-nao-importa-compra` de `setup.cfg` falha se um dia importar.
"""

from dataclasses import dataclass, field
from typing import Sequence

from mini_orion.pagamentos._cobrancas import RegistroCobranca
from mini_orion.pagamentos.api import ResultadoCobranca


@dataclass(frozen=True)
class Lancamento:
    """Uma linha do extrato do provedor."""

    chave: str
    valor: float


@dataclass
class RelatorioConciliacao:
    conferem: list[str] = field(default_factory=list)
    valor_divergente: list[str] = field(default_factory=list)
    so_no_provedor: list[str] = field(default_factory=list)  # cobrado, sem registro no Orion
    so_no_orion: list[str] = field(default_factory=list)  # registrado como aprovado, sem lancamento

    @property
    def fecha(self) -> bool:
        return not (self.valor_divergente or self.so_no_provedor or self.so_no_orion)


def conciliar(
    registros: Sequence[RegistroCobranca], extrato: Sequence[Lancamento]
) -> RelatorioConciliacao:
    aprovadas = {
        r.chave: r for r in registros if r.resultado is ResultadoCobranca.APROVADA
    }
    lancados = {lancamento.chave: lancamento for lancamento in extrato}
    relatorio = RelatorioConciliacao()
    for chave, lancamento in lancados.items():
        registro = aprovadas.get(chave)
        if registro is None:
            relatorio.so_no_provedor.append(chave)
        elif registro.valor != lancamento.valor:
            relatorio.valor_divergente.append(chave)
        else:
            relatorio.conferem.append(chave)
    relatorio.so_no_orion = [chave for chave in aprovadas if chave not in lancados]
    return relatorio

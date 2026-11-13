"""O acordo de formato entre `compra` e `pagamentos`, escrito uma vez.

Pela rede, o que `pagamentos` responde e uma interface publica, com
consumidores que ele nao controla. Este modulo guarda o vocabulario do
acordo e as duas maneiras de um consumidor ler uma resposta:

- `ler_ingenuo` reproduz um consumidor da v1 que decide pelo que conhece
  e trata todo o resto como aprovacao. E o erro que a Aula 18 mostra.
- `leitor_tolerante` ignora campos que nao conhece, mas trata um valor
  que nao conhece como falha: nunca como aprovacao.

A versao do consumidor e o conjunto de valores que ele conhece.
"""

from typing import Callable

from mini_orion.pagamentos.api import CobrancaIndeterminada, ResultadoCobranca
from mini_orion.rede.api import Carga

RESULTADOS_V1 = frozenset(
    {
        "aprovada",
        "recusada_pelo_emissor",
        "acima_do_limite",
        "provedor_indisponivel",
    }
)
# A v2 so acrescenta um valor. Nenhum campo mudou de nome ou de tipo.
RESULTADOS_V2 = RESULTADOS_V1 | {"em_analise"}

Leitor = Callable[[Carga], ResultadoCobranca]


class ResultadoDesconhecido(CobrancaIndeterminada):
    """A resposta chegou, mas diz algo que o consumidor nao sabe ler."""


def ler_ingenuo(carga: Carga) -> ResultadoCobranca:
    # Decide pelo que conhece da v1 e deixa o resto virar aprovacao.
    valor = carga["resultado"]
    if valor in RESULTADOS_V1 - {"aprovada"}:
        return ResultadoCobranca(str(valor))
    return ResultadoCobranca.APROVADA


def leitor_tolerante(conhecidos: frozenset[str]) -> Leitor:
    def ler(carga: Carga) -> ResultadoCobranca:
        valor = carga.get("resultado")  # campos extras sao ignorados
        if valor not in conhecidos:
            raise ResultadoDesconhecido(f"resultado {valor!r} fora do acordo")
        return ResultadoCobranca(str(valor))

    return ler

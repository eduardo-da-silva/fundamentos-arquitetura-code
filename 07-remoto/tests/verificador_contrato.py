"""Verificador do contrato escrito pelo consumidor.

O consumidor (`compra`) declara em `contratos/` o que espera de cada
resposta: quais campos, de que tipo, com quais valores. O produtor
(`pagamentos`) roda este verificador contra o proprio servidor antes de
publicar. Campos que o consumidor nao menciona sao livres: acrescentar um
campo nunca quebra o acordo.
"""

import json
from pathlib import Path

CONTRATO = Path(__file__).resolve().parent.parent / "contratos" / "compra-espera-de-pagamentos.json"
TIPOS = {"texto": str, "numero": (int, float), "booleano": bool}


def carregar() -> dict:
    return json.loads(CONTRATO.read_text(encoding="utf-8"))


def violacoes(resposta: dict, esperado: dict) -> list[str]:
    achados = []
    for campo, regra in esperado.items():
        if campo not in resposta:
            achados.append(f"campo '{campo}' ausente")
            continue
        valor = resposta[campo]
        if not isinstance(valor, TIPOS[regra["tipo"]]):
            achados.append(f"campo '{campo}' deveria ser {regra['tipo']}")
        elif "valores" in regra and valor not in regra["valores"]:
            achados.append(f"campo '{campo}' com valor '{valor}' fora do acordo")
    return achados


def verificar(tratador) -> list[str]:
    """Roda todas as interacoes do contrato contra o tratador do produtor."""
    achados = []
    for interacao in carregar()["interacoes"]:
        resposta = tratador(dict(interacao["pedido"]))
        for achado in violacoes(resposta, interacao["resposta"]):
            achados.append(f"{interacao['descricao']}: {achado}")
    return achados

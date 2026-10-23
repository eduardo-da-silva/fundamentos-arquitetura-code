# Mini-Orion Checkout

Recorte executável do Marketplace Orion, usado como exemplo do professor ao longo do Módulo 1.

Não é um sistema de produção: não há persistência real, framework web nem concorrência. Ele existe para tornar visível o efeito de decisões estruturais — em especial, para mostrar que **arquitetura se manifesta primeiro como dificuldade de testar**.

## Os estados

| Pasta | Estado | Aulas |
|---|---|---|
| `01-acoplado/` | cobrança e notificação dentro do fluxo, provedor concreto instanciado no construtor | 1 e 2 |
| `02-fronteiras/` | `Gateway` como `Protocol`, notificação fora do caminho crítico, ciclo quebrado | 3 a 5 |
| `03-governado/` | connascências reduzidas, contratos isolados, decisões verificadas automaticamente | 6 a 8 |
| `04-camadas/` | pacote em camadas técnicas, contrato `layers` (aberto) + `forbidden` domínio/aplicação ↛ infraestrutura | 10 |
| `05-modular/` | módulos de domínio com API pública e internals `_*`, contratos `independence`/`forbidden` | 11 e 12 |
| `06-microkernel/` | `Promocoes` como registro de plugins, contrato núcleo ↛ plugins concretos | 13 |
| `07-remoto/` | `Pagamentos` atrás de uma rede simulada: latência, falha parcial, repetição com chave de idempotência, contrato `rede` ↛ domínio | 16 |

Cada estado parte do anterior. Ler os estados em sequência é o exercício.

A leitura mais proveitosa continua sendo comparar os contratos de `setup.cfg` de um estado para o outro antes de comparar o código: a decisão arquitetural muda primeiro na verificação executável.

## O que observar em cada passagem

**De `01` para `02`** — compare os arquivos de teste antes de comparar o código. Três testes que eram impossíveis no primeiro estado passam a ser triviais no segundo: trocar de provedor, simular falha de notificação, fechar um pedido sem disparar efeito externo. Nenhum deles menciona arquitetura, e todos só existem por causa dela.

**De `02` para `03`** — repare no `test_falha_de_notificacao_nao_invalida_a_compra`. No estado `02` ele documenta uma fronteira **incompleta**: o teste espera a exceção subir. No `03` ele espera a compra sobreviver. O teste mudou de expectativa porque a decisão mudou, e o histórico dessa mudança é o conteúdo da aula.

**No `03`** — o módulo `contratos.py` existe por um motivo estrutural, não estético. Se `checkout` importasse `Notificador` de dentro de `notificacoes`, nenhuma ferramenta conseguiria distinguir "depende do contrato" de "depende da implementação": no nível do `import`, são a mesma coisa.

## Rodando

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

cd 03-governado
pytest                    # 9 testes
lint-imports              # 3 contratos arquiteturais
```

## Os contratos como teste

`03-governado/setup.cfg` declara três decisões arquiteturais como verificação executável:

- `checkout` não pode importar `pagamentos` nem `notificacoes`;
- `contratos` não pode importar nenhuma implementação;
- não pode haver ciclo entre os componentes.

Para ver a diferença que isso faz, desfaça uma decisão de propósito. Adicione ao topo de `03-governado/mini_orion/checkout.py`:

```python
import mini_orion.pagamentos
```

Rode `lint-imports` e depois `pytest`. Os dois falham, apontando a linha. O sistema continuaria funcionando perfeitamente — nenhum comportamento mudou — e é exatamente esse o ponto: **degradação arquitetural não quebra nada hoje.** Ela cobra depois, quando trocar de provedor já não é mais barato.

Um acordo verbal em reunião não sobrevive à rotatividade do time. Um contrato que falha na CI, sim.

## Verificando o grafo de dependências

```bash
cd 03-governado
pydeps mini_orion --max-bacon=2 --cluster
```

O grafo extraído do código é a única fonte confiável. O desenho no quadro e o código divergem em questão de semanas, e quando divergem é sempre o desenho que está errado.

## A rede simulada (a partir do `07-remoto`)

O Mini-Orion não abre socket nem cria thread. Para ensinar distribuição sem abrir essa porta, `07-remoto/mini_orion/rede/` traz um transporte simulado em processo: latência, timeout e falha parcial são parâmetros (as hipóteses de trabalho da Aula 16), o sorteio usa semente fixa e o relógio é injetado. Nenhum teste dorme e nenhum é intermitente.

Ele reproduz a **forma** do problema (tempo que não é zero, falha que não é exceção local, estado ambíguo), não a física da rede.

```bash
cd 07-remoto
pytest            # 47 testes
lint-imports      # 5 contratos
python ensaio.py  # reproduz as tabelas da Aula 16 (use --varrer para ver a variação entre sementes)
python quantum.py # a conta da Aula 17: artefatos, arestas remotas e quanta de cada forma
python ensaio_generico.py  # o ensaio da Aula 16 sem o Orion, para aplicar a um cenario proprio
```

O teste que vale ler primeiro é `tests/test_remoto.py::test_repeticao_sem_chave_cobra_duas_vezes`, ao lado do seu par com chave.

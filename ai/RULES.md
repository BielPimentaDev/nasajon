# RULES – Projeto Enriquecimento IBGE

Estas regras servem para guiar todo o desenvolvimento do projeto.

## 1. Objetivos gerais
- Manter o código simples, legível e fácil de evoluir.
- Aplicar princípios de orientação a objetos e SOLID, sem over engineering.
- Usar TDD sempre que possível: escrever (ou ao menos projetar) testes antes da implementação.
- Manter separação clara de responsabilidades (arquitetura hexagonal moderada).

## 2. Arquitetura (hexagonal moderada)
- Teremos três tipos principais de componentes:
  - **Domínio**: regras de negócio (entidades, serviços de domínio, cálculos de estatísticas, lógica de matching de municípios, etc.).
  - **Aplicação (casos de uso)**: orquestra fluxo de leitura do CSV, uso do domínio, escrita do resultado e envio para a Edge Function.
  - **Infraestrutura / Adapters**: tudo que toca o “mundo externo” (arquivos, HTTP, variáveis de ambiente, console, etc.).
- Dependências SEMPRE apontam do externo para o interno:
  - Domínio **não** depende de módulos de infraestrutura (requests, leitura de arquivos, etc.).
  - Casos de uso conhecem o domínio e conversam com a infraestrutura apenas via interfaces (ports) ou abstrações simples.
  - Adapters implementam essas interfaces e podem usar bibliotecas externas.
- Evitar múltiplas camadas extras (ex.: “services”, “managers”, “controllers” genéricos) se não forem necessários.

## 3. Organização de código (sugestão)
- `domain/`
  - Entidades (ex.: `Municipio`, `LinhaResultado`, `Estatisticas`).
  - Serviços de domínio (ex.: `MunicipioMatcher`, `CalculadoraEstatisticas`).
- `application/`
  - Casos de uso (ex.: `ProcessarMunicipiosUseCase`).
  - Orquestração do fluxo principal.
- `adapters/`
  - `ibge/`: cliente IBGE (HTTP), mapeamento da resposta para entidades de domínio.
  - `edge/`: cliente da Edge Function de correção.
  - `io/`: leitura/escrita de CSV, leitura de configs/variáveis de ambiente, log simples.
- `tests/`
  - Seguir mesma estrutura de pastas do código de produção.

## 4. Uso de classes, OO e SOLID
- Preferir classes quando existir estado ou comportamento coeso (ex.: matcher de municípios, cliente IBGE, caso de uso principal).
- Funções livres são aceitáveis para operações puramente utilitárias e sem dependências (ex.: normalização de strings).
- **Responsabilidade Única (SRP)**:
  - Cada classe deve ter um motivo claro para mudar.
  - Ex.: `MunicipioMatcher` não deve se preocupar com chamadas HTTP ao IBGE; ele recebe dados já carregados.
- **Aberto/Fechado (OCP)**:
  - Facilitar inclusão de novos adapters (ex.: outro provedor de dados) sem mudar o domínio.
- **Liskov / Interface Segregation / Dependency Inversion**:
  - Definir interfaces/abstrações simples para clientes externos (ex.: `IBGEMunicipioRepository`, `StatsSender`).
  - Application depende de interfaces, não de implementações concretas (adapters as dependências reais).

## 5. Adapters para integrações externas
- Toda comunicação externa deve passar por adapters dedicados:
  - IBGE API (HTTP).
  - Edge Function (HTTP POST com ACCESS_TOKEN).
  - Sistema de arquivos (leitura/escrita de CSV).
  - Configuração (variáveis de ambiente/constantes).
- Regra: **nenhum código de domínio ou caso de uso deve chamar diretamente `requests`, ler arquivos ou acessar `os.environ`**.
- Tratamento de erros de rede/IO fica nos adapters; o domínio recebe respostas claras (sucesso/erro) via objetos/resultado.

## 6. TDD e testes
- Sempre que possível, seguir o ciclo TDD (Red → Green → Refactor):
  1. Escrever teste que falha (ex.: comportamento esperado do matching ou cálculo de estatísticas).
  2. Implementar a menor quantidade de código para passar o teste.
  3. Refatorar mantendo os testes passando.
- Priorizar testes para:
  - Lógica de matching de municípios (normalização, correções, fuzzy matching).
  - Cálculo de estatísticas (totais, médias por região).
  - Comportamento dos casos de uso (ex.: processamento completo com stubs/fakes dos adapters externos).
- Nos testes de domínio e application, **mockar ou fakes** para adapters externos (IBGE, Edge, IO).
- Garantir que os testes possam rodar offline (sem dependência real da API do IBGE ou Edge Function).

## 7. Simplicidade e anti over-engineering
- Antes de criar uma nova camada/classe, perguntar: “resolve um problema real agora?”
- Evitar:
  - Padrões complexos desnecessários (ex.: builders genéricos, factories abstratas, etc.).
  - Criar interfaces genéricas sem necessidade concreta.
- Manter o número de classes razoável e focado nas regras de negócio.

## 8. Convenções gerais
- Nomear classes, métodos, funções e variáveis em inglês, usando snake_case para funções/variáveis e PascalCase para classes; evitar misturar idiomas no mesmo módulo.
- Manter funções/métodos pequenos e focados.
- Tratar erros de forma previsível, retornando tipos claros (ex.: Result/enum de status) em vez de espalhar exceções não tratadas.
- Preferir imutabilidade onde fizer sentido (ex.: entidades de domínio simples).
- Para comunicação HTTP em adapters, seguir estilo REST sempre que possível: recursos substantivos no plural (por exemplo, /municipalities), métodos HTTP adequados (GET para leitura, POST para envio de stats) e nomes de métodos de cliente que expressem claramente a operação (por exemplo, get_all_municipalities, post_stats).
- Mesmo que a API externa não siga estritamente REST, manter a nomenclatura interna coerente com REST e em inglês (por exemplo, IbgeMunicipalityClient, EdgeStatsClient).

## 9. Relatório final
- Ao final do desenvolvimento, será produzido um relatório resumindo:
  - Estrutura final de pastas e principais classes.
  - Decisões de arquitetura (onde aplicamos hexagonal/OO/SOLID).
  - Estratégia de TDD e cobertura dos testes.
  - Como os adapters externos foram implementados e testados.
- Esse relatório deve ser coerente com estas RULES e refletir o que foi realmente implementado.

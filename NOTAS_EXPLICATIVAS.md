# Notas Explicativas

## Lógica de matching de municípios

- A lista completa de municípios é carregada uma vez via adapter de IBGE (RequestsIbgeMunicipalityGateway), que consome o endpoint oficial de localidades e mapeia para entidades de domínio IbgeMunicipality.
- O matcher de domínio (MunicipalityMatcher) recebe essa lista e não conhece HTTP nem detalhes da API externa.
- Para cada município de entrada (MunicipalityInput):
  - O nome é normalizado (normalize_municipality_name):
    - `strip()` + `lower()`.
    - Remoção de acentos.
    - Substituição de hífens por espaço.
    - Colapso de múltiplos espaços.
  - Primeiro é feita uma busca exata nesse espaço normalizado:
    - 1 candidato → `status = OK`.
    - >1 candidato → `status = AMBIGUO`.
  - Se não houver match exato, é feito fuzzy matching com distância de Levenshtein:
    - Calcula-se a distância entre o nome normalizado de entrada e todos os nomes normalizados da base IBGE.
    - Mantém-se apenas os candidatos com distância mínima.
    - Se a distância mínima for maior que 2 → `status = NAO_ENCONTRADO`.
    - Se houver apenas 1 melhor candidato dentro do limiar → `status = OK`.
    - Se houver mais de um melhor candidato dentro do limiar → `status = AMBIGUO`.
- Essa estratégia foi calibrada para resolver os exemplos do PRD ("Belo Horzionte", "Curitba", "Santoo Andre"), tolerando pequenos typos sem ser agressiva demais.

## Estratégia de cálculo das estatísticas

- A agregação é feita pela classe de domínio StatsCalculator, a partir de uma coleção de ResultLine já processadas.
- Cálculos principais:
  - `total_municipalities`: número total de linhas em resultado.csv (incluindo todos os status).
  - `total_ok`: quantidade de linhas consideradas "efetivamente OK" para fins de estatística:
    - linhas com `status = OK`; e
    - linhas com `status = AMBIGUO` que possuem município IBGE escolhido (campos de região/código preenchidos).
  - `total_not_found`: quantidade de linhas com `status = NAO_ENCONTRADO`.
  - `total_api_error`: quantidade de linhas com `status = ERRO_API`.
  - `pop_total_ok`: soma de `population_input` apenas das linhas consideradas "efetivamente OK" (OK + AMBIGUO com dados IBGE).
  - `average_by_region`:
    - Para cada região (campo `region` nas linhas "efetivamente OK"), agrupa-se as populações.
    - Calcula-se a média simples por região (soma / quantidade de linhas OK naquela região).
    - Linhas sem dados de IBGE (por exemplo, `NAO_ENCONTRADO` ou `ERRO_API`, ou AMBIGUO sem região) não participam do cálculo das médias.
- O objeto imutável Stats carrega esses campos em inglês; o adapter da Edge Function faz o mapeamento de nomes para o JSON final exigido (por exemplo, `total_municipalities` → `total_municipios`).

## Tratamento de erros de API e atalhos arquiteturais

### IBGE

- O adapter RequestsIbgeMunicipalityGateway encapsula toda a comunicação com a API de localidades do IBGE.
- Erros tratados:
  - Timeout de rede → lança IbgeClientError com mensagem clara e loga o erro.
  - Erros genéricos de requests (problemas de conexão, DNS, etc.) → lança IbgeClientError e registra log com detalhes.
  - Status HTTP diferente de 200 → lança IbgeClientError com a mensagem "Unexpected status from IBGE API: <status_code>" e loga o status retornado.
  - JSON inválido ou payload não-lista → lança IbgeClientError com mensagens específicas e registra log.
  - Itens individuais com estrutura inesperada no payload → são ignorados com um log em nível WARNING, sem derrubar todo o processamento.
- Na camada de aplicação (ProcessMunicipalitiesUseCase), qualquer exceção vinda do gateway IBGE é capturada e tratada como falha externa controlada:
  - Todas as linhas de entrada recebem `status = ERRO_API`.
  - resultado.csv ainda é gerado.
  - As estatísticas locais são calculadas com base nessas linhas (por exemplo, `total_api_error` = total de linhas).

### Edge Function

- O adapter RequestsEdgeStatsClient é responsável por enviar o objeto de domínio Stats para a Edge Function.
- Configuração vem de EnvConfig (via variáveis de ambiente ou arquivo .env):
  - `PROJECT_FUNCTION_URL`.
  - `ACCESS_TOKEN`.
- Regras de tratamento de erros no envio:
  - Se URL ou token estiverem ausentes, nenhum POST é feito; o método retorna EdgeResponse com `success = False` e uma mensagem de erro amigável, e um log WARNING é emitido.
  - Timeouts e falhas de rede são capturados, convertidos em EdgeResponse com `success = False` e `error_message` descritiva, e o erro é logado.
  - Status HTTP diferente de 200 também gera EdgeResponse de falha, com mensagem contendo o status e log de erro.
  - JSON inválido na resposta da Edge Function resulta em EdgeResponse de falha, com log correspondente.
  - Em caso de sucesso, o adapter extrai `score` (float) e `feedback` (string) quando presentes, registra um log informativo e retorna EdgeResponse com `success = True`.
- O caso de uso principal nunca falha por causa de problemas de Edge Function; ele sempre recebe um EdgeResponse (de sucesso ou falha), e o CLI imprime a nota quando disponível ou uma mensagem explicando por que o score não está disponível.

### Atalhos arquiteturais

- A arquitetura segue o modelo hexagonal moderado descrito em ai/RULES.md:
  - Domínio não conhece bibliotecas externas nem detalhes de IO/HTTP.
  - A aplicação depende apenas de ports (IbgeMunicipalityGateway, StatsSender, etc.).
  - Adapters concretos (HTTP, CSV, env) implementam esses ports.
- Atalhos assumidos de forma consciente:
  - O script principal main.py ajusta sys.path para incluir a pasta src, simplificando a execução via `python main.py` sem empacotamento adicional.
  - Logs são simples (logging básico no console), suficientes para depuração local, sem camadas extras de observabilidade.
  - A base de municípios do IBGE é carregada integralmente em memória, o que é aceitável para o tamanho atual do dataset.

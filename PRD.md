# PRD – Enriquecimento de Municípios com IBGE e Envio para Edge Function

## 1. Visão Geral
Produto: script/aplicação de linha de comando em Python que processa um arquivo CSV de municípios e populações, enriquece os dados usando a API de localidades do IBGE, gera um CSV de resultado, calcula estatísticas agregadas e envia essas estatísticas para uma API de correção (Edge Function) autenticada via ACCESS_TOKEN, exibindo a nota (score) retornada.

Público-alvo: desenvolvedores/avaliadores técnicos que executarão o script localmente para validar conhecimento de integração com APIs, manipulação de dados e boas práticas de código.

## 2. Objetivos do Produto
- Automatizar o enriquecimento de um conjunto de municípios com dados oficiais do IBGE.
- Gerar um arquivo de saída padronizado (resultado.csv) com status de matching para cada município.
- Calcular e enviar estatísticas consolidadas para uma Edge Function que retorna um score de correção.
- Demonstrar qualidade de código (OO, SOLID, TDD, arquitetura hexagonal moderada) e tratamento robusto de erros.

## 3. Escopo Funcional
### 3.1 Leitura de input.csv
- O sistema deve ler um arquivo CSV de entrada com o nome fixo `input.csv` localizado no diretório do projeto (ou em caminho configurável, se for decidido em design).
- O formato do arquivo é exatamente:
  - Cabeçalho: `municipio,populacao`.
  - Linhas de exemplo (obrigatórias para o exercício):
    - Niteroi,515317
    - Sao Gonçalo,1091737
    - Sao Paulo,12396372
    - Belo Horzionte,2530701
    - Florianopolis,516524
    - Santo Andre,723889
    - Santoo Andre,700000
    - Rio de Janeiro,6718903
    - Curitba,1963726
    - Brasilia,3094325
- A coluna `populacao` deve ser interpretada como número inteiro.

### 3.2 Enriquecimento com API de localidades do IBGE
- O sistema deve consumir a API pública de localidades do IBGE:
  - Documentação: https://servicodados.ibge.gov.br/api/docs/localidades
- Deve obter, para cada município da entrada, os seguintes dados oficiais do IBGE:
  - `municipio_ibge`: nome oficial do município.
  - `uf`: sigla da unidade federativa.
  - `regiao`: nome da região (Norte, Nordeste, Centro-Oeste, Sudeste, Sul).
  - `id_ibge`: código numérico do município.
- Estratégia mínima suportada:
  - Pode fazer GET geral em `https://servicodados.ibge.gov.br/api/v1/localidades/municipios` e montar estrutura em memória para matching.
  - Alternativamente, pode usar outros endpoints desde que atenda aos dados mínimos acima.
- A lógica de matching entre o `municipio` do input e os dados do IBGE deve:
  - Considerar diferenças de acentuação e maiúsculas/minúsculas.
  - Tratar pequenos erros de digitação (ex.: "Belo Horzionte", "Curitba", "Santoo Andre").
  - Ser tolerante, porém previsível e determinística.
- O sistema deve classificar o resultado do matching em um campo `status` com valores possíveis:
  - `OK` – município encontrado de forma clara e única.
  - `NAO_ENCONTRADO` – nenhum município compatível suficiente encontrado.
  - `ERRO_API` – erro ao acessar ou processar resposta da API do IBGE.
  - `AMBIGUO` – mais de um município possível e a lógica optar por não decidir.

### 3.3 Geração do arquivo resultado.csv
- O sistema deve gerar um arquivo CSV `resultado.csv` com as colunas, nesta ordem:
  - `municipio_input`
  - `populacao_input`
  - `municipio_ibge`
  - `uf`
  - `regiao`
  - `id_ibge`
  - `status`
- Regras de preenchimento:
  - `municipio_input` e `populacao_input` são copiados do input.
  - `municipio_ibge`, `uf`, `regiao`, `id_ibge` são preenchidos apenas quando houver matching bem-sucedido (`OK`), ou conforme regras definidas para `AMBIGUO` (por padrão, podem ficar vazios em casos não OK).
  - Para status `NAO_ENCONTRADO` ou `ERRO_API`, os campos de dados do IBGE podem ficar vazios.
- Encoding esperado: UTF-8, delimitador vírgula.

### 3.4 Cálculo de estatísticas
Após processar todos os municípios, o sistema deve calcular:
- `total_municipios`: quantidade total de linhas processadas no input.
- `total_ok`: quantidade de linhas com `status = "OK"`.
- `total_nao_encontrado`: quantidade de linhas com `status = "NAO_ENCONTRADO"`.
- `total_erro_api`: quantidade de linhas com `status = "ERRO_API"`.
- `pop_total_ok`: soma das populações (`populacao_input`) de linhas com `status = "OK"`.
- `medias_por_regiao`:
  - Para cada `regiao`, calcular a média de `populacao_input` somente sobre linhas com `status = "OK"`.
  - Exemplo de estrutura:
    ```json
    "medias_por_regiao": {
      "Sudeste": 999999.17,
      "Sul": 999999.0,
      "Centro-Oeste": 999999.0
    }
    ```
- As estatísticas devem ser montadas em um objeto `stats` com a seguinte estrutura final:
  ```json
  {
    "stats": {
      "total_municipios": 99,
      "total_ok": 99,
      "total_nao_encontrado": 99,
      "total_erro_api": 99,
      "pop_total_ok": 99999,
      "medias_por_regiao": {
        "Sudeste": 999999.17,
        "Sul": 999999.0,
        "Centro-Oeste": 999999.0
      }
    }
  }
  ```
  (os valores são apenas ilustrativos).

### 3.5 Envio das estatísticas para Edge Function
- Ao final da execução, o sistema deve:
  - Ler de configuração/ambiente:
    - `PROJECT_FUNCTION_URL` (URL da Edge Function de correção).
    - `ACCESS_TOKEN` (token de acesso).
  - Fazer um POST HTTP para `PROJECT_FUNCTION_URL` com:
    - Header `Authorization: Bearer <ACCESS_TOKEN>`.
    - Header `Content-Type: application/json`.
    - Corpo JSON contendo o objeto `stats` calculado.
- Exemplo de chamada (para referência conceitual):
  ```bash
  curl -X POST "$PROJECT_FUNCTION_URL" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "stats": {
        "total_municipios": 99,
        "total_ok": 9,
        "total_nao_encontrado": 9,
        "total_erro_api": 0,
        "pop_total_ok": 99999,
        "medias_por_regiao": {
          "Sudeste": 999999.7,
          "Sul": 99999.0,
          "Centro-Oeste": 99999.0
        }
      }
    }'
  ```
- O sistema deve ler a resposta JSON da Edge Function, que possui o formato:
  ```json
  {
    "user_id": "uuid...",
    "email": "seu_email@exemplo.com",
    "score": 8.75,
    "feedback": "Muito bom! Seu resultado está bem próximo do gabarito.",
    "components": { ... }
  }
  ```
- O sistema deve:
  - Imprimir pelo menos o campo `score` no console.
  - Opcionalmente, imprimir também o `feedback`.

## 4. Requisitos Não Funcionais
- Linguagem primária: Python.
- Estilo arquitetural: arquitetura hexagonal moderada, conforme RULES.md:
  - Separação entre Domínio, Aplicação (casos de uso) e Adapters/Infraestrutura.
  - Uso de classes e princípios de orientação a objetos e SOLID sem over engineering.
  - Adapters para integrações externas (API IBGE, Edge Function, IO de arquivos, configuração).
- Qualidade de código:
  - Código legível, organizado por responsabilidade.
  - Tratamento explícito de erros de rede, parsing e IO.
  - Logs/mensagens simples para facilitar entendimento em caso de falhas.
- Testes:
  - Uso de TDD sempre que possível.
  - Cobertura mínima das principais regras de negócio: matching e cálculo de estatísticas.
  - Testes não devem depender da disponibilidade real das APIs externas (utilizar mocks/fakes).

## 5. Fluxo de Usuário (alto nível)
1. Usuário garante que `input.csv` está no local esperado.
2. Usuário configura `PROJECT_FUNCTION_URL` e `ACCESS_TOKEN` (por variáveis de ambiente ou outro mecanismo definido em implementação).
3. Usuário executa o comando principal (por exemplo, `python -m app` ou `python main.py`).
4. Sistema:
   - Lê `input.csv`.
   - Carrega/consulta dados do IBGE.
   - Faz matching e enriquece cada linha, gerando `resultado.csv`.
   - Calcula as estatísticas e monta o objeto `stats`.
   - Envia `stats` para a Edge Function.
   - Exibe o `score` (e, opcionalmente, `feedback`) no console.
5. Usuário inspeciona `resultado.csv`, o output do console e, se necessário, os logs.

## 6. Casos de Erro e Comportamento Esperado
- **API do IBGE indisponível**:
  - O sistema registra o erro de forma clara.
  - As linhas afetadas devem receber status `ERRO_API`.
  - `resultado.csv` ainda deve ser gerado.
- **Erro de rede ou resposta inválida da Edge Function**:
  - O sistema informa que não foi possível obter o score.
  - Não impede a geração de `resultado.csv` nem o cálculo das estatísticas locais.
- **Município não encontrado após matching**:
  - Linha marcada com `NAO_ENCONTRADO`.
- **Matching ambíguo (múltiplos candidatos)**:
  - Linha marcada com `AMBIGUO` (caso esse tratamento seja implementado).
- **Entrada inválida de população (não numérica)**:
  - Estratégia a ser decidida e documentada (ex.: descartar linha, marcar status especial). Para o dataset padrão, este caso não deve ocorrer.

## 7. Critérios de Aceitação
- Dado o `input.csv` especificado, ao rodar o sistema:
  - Um arquivo `resultado.csv` é gerado com o cabeçalho e número de linhas esperado.
  - Cada linha possui um dos status válidos: `OK`, `NAO_ENCONTRADO`, `ERRO_API`, `AMBIGUO`.
  - Pelo menos parte significativa dos municípios é classificada como `OK` com dados corretos (nome IBGE, UF, região, id_ibge).
- As estatísticas calculadas são consistentes com o conteúdo de `resultado.csv`.
- O sistema realiza uma requisição POST à Edge Function com o formato de JSON exigido e headers apropriados.
- O sistema exibe o `score` retornado no console quando a Edge Function responde com sucesso.
- Código está organizado de acordo com as regras definidas em RULES.md.

## 8. Métricas de Sucesso
- Correção do conteúdo de `resultado.csv` (matching e campos IBGE).
- Precisão das estatísticas calculadas em relação ao input.
- Ausência de falhas não tratadas na presença de erros de rede ou dados inesperados.
- Clareza do código e facilidade de entendimento das principais decisões de design.
- Feedback positivo (score alto) retornado pela Edge Function de correção.

## 9. Entregáveis
- Código-fonte completo do projeto, seguindo a organização proposta (domínio, aplicação, adapters, testes).
- Arquivo `input.csv` (conforme especificação).
- Arquivo `resultado.csv` gerado por uma execução de exemplo.
- "Notas Explicativas" documentando:
  - Lógica de matching (normalização, tratamento de erros de digitação, critérios para AMBIGUO/NAO_ENCONTRADO).
  - Estratégia de cálculo das estatísticas.
  - Tratamento de erros de API e atalhos arquiteturais tomados.
- README curto explicando:
  - Como instalar dependências.
  - Como configurar `PROJECT_FUNCTION_URL` e `ACCESS_TOKEN`.
  - Como executar o programa.

## 10. Restrições e Considerações
- O uso de IA é permitido, mas o desenvolvedor deve entender o código entregue e ser capaz de explicá-lo em uma conversa técnica.
- Não é necessário criar interface gráfica; a interação será via linha de comando/console.
- O PRD deve ser seguido em conjunto com RULES.md, que define padrões arquiteturais e de desenvolvimento (OO, SOLID, TDD, adapters, simplicidade).
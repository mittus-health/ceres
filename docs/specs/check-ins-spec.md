# SPEC — Primeira implementação de check-ins

**Status:** API implementada e verificada; contrato disponível para integração com o frontend.
**Escopo:** API de check-ins no backend NestJS, persistência via Prisma/PostgreSQL e contrato para integração com o calendário.
**Referências:** [schema Prisma](../../backend/prisma/schema.prisma), [especificação de dados](../check-ins-database.md) e [features do MVP](../../FEATURES.md).

## 1. Objetivo

Permitir que um astronauta da demonstração registre sono, estresse, humor, conflito na equipe e fadiga; corrija o registro do dia; e consulte o histórico por sessão. O registro deve continuar disponível após recarregar a página.

O primeiro fluxo integrado será:

1. Consultar o calendário e estabelecer a sessão de demonstração.
2. Preencher o check-in do dia.
3. Salvar o registro pela API.
4. Consultar novamente o calendário e visualizar o registro salvo.
5. Recarregar a página e recuperar os mesmos dados pela sessão.

Nomes de campos, mensagens da API e textos apresentados no aplicativo devem estar em inglês. A documentação pode permanecer em português.

## 2. Base existente e decisões

### Confirmado

- O banco é PostgreSQL no Supabase; o backend acessa o banco com credenciais de servidor.
- O modelo `CheckIn` está mapeado para `check_ins`.
- Há no máximo um check-in por `(session_id, check_in_date)`.
- Sono e as quatro escalas são obrigatórios; `description` é opcional.
- As tabelas de opções das escalas já existem e são referenciadas por chaves estrangeiras.
- `check_in_actions` já existe, mas seu processamento será uma implementação posterior.

### Decisões confirmadas para esta primeira versão

As cinco propostas abaixo foram aprovadas e devem orientar a implementação:

| Tema | Decisão |
| --- | --- |
| Dia de referência | UTC; o backend é a autoridade para determinar o dia atual. |
| Escrita | Criar e substituir apenas o check-in do dia atual. |
| Histórico | Consultar registros anteriores; datas passadas e futuras não são graváveis nesta versão. |
| Descrição | Texto livre opcional, com até 2.000 caracteres após remoção de espaços nas extremidades. |
| Sessão | Sessão anônima de demonstração por cookie assinado, com validade fixa de 30 dias. |

O intervalo de sono de 0 a 24 horas e as escalas abaixo já são impostos pelo banco. Alterar a regra de datas no futuro não exigirá mudar os tipos das colunas.

## 3. Dados e validação

Os nomes na API usam `snake_case`; os campos do Prisma usam `camelCase` e `@map` para as colunas correspondentes.

| Campo da API | Campo Prisma | Regra |
| --- | --- | --- |
| `sleep_hours` | `sleepHours` | Número finito entre 0 e 24, com no máximo duas casas decimais. |
| `stress_level` | `stressLevel` | Inteiro de 1 a 5: `Very calm` → `Very stressed`. |
| `mood_level` | `moodLevel` | Inteiro de 1 a 5: `Very happy / positive` → `Very sad / negative`. |
| `team_conflict_level` | `teamConflictLevel` | Inteiro de 1 a 5; usar os rótulos cadastrados na tabela de opções. |
| `fatigue` | `fatigue` | Inteiro de 1 a 7: `Fully alert and wide awake` → `Completely exhausted and unable to function effectively`. |
| `description` | `description` | String ou `null`; campo omitido, `null` ou texto vazio após trim resulta em `null`. |

Regras adicionais:

- Rejeitar campos desconhecidos, inclusive `session_id`, `id`, `created_at` e `updated_at` no corpo de escrita.
- Rejeitar strings numéricas, booleanos, arrays e objetos onde se espera número. Não converter silenciosamente `"3"` em `3`.
- Todos os indicadores devem estar presentes em cada `PUT`. Não implementar atualização parcial.
- Datas devem estar em `YYYY-MM-DD` e existir no calendário; rejeitar, por exemplo, `2026-02-30`.
- Tratar `check_in_date` como data sem horário. Usar uma conversão consistente em UTC na fronteira do Prisma, sem deslocamento pelo fuso do processo.
- Serializar `sleep_hours` como número JSON, mesmo que o Prisma o represente como `Decimal`.
- Serializar `created_at` e `updated_at` como instantes ISO 8601 em UTC.

**Rótulos de conflito — confirmado:** manter os rótulos cadastrados no banco. A API deve retorná-los sem criar outra lista divergente:

| Valor | Rótulo |
| --- | --- |
| 1 | No team conflict |
| 2 | Low team conflict |
| 3 | Moderate team conflict |
| 4 | High team conflict |
| 5 | Very high team conflict |

## 4. Sessão de demonstração

- Cookie: `mittus_session`, contendo UUID gerado no servidor e assinatura verificável.
- O servidor cria uma sessão quando o cookie está ausente, inválido ou expirado. Uma nova sessão começa sem histórico.
- O mesmo cookie é usado nas três rotas de check-ins e na rota de opções.
- Usar `HttpOnly`, `Path=/`, `SameSite=Lax`, `Max-Age=2592000` e `Secure` em produção. A assinatura deve incluir a expiração e usar um segredo exclusivo do servidor.
- Não aceitar um UUID arbitrário enviado pelo cliente como sessão válida. Não retornar o identificador da sessão no JSON.
- Toda consulta deve filtrar por `sessionId`. Toda escrita deve obter esse valor exclusivamente da sessão validada.
- Apagar ou expirar o cookie encerra o acesso àquele histórico; recuperação entre dispositivos não faz parte do fluxo anônimo.
- As respostas de registros devem usar `Cache-Control: private, no-store`.

Para a integração web, o cliente deve enviar `credentials: 'include'`. Se as origens forem diferentes, o backend deve permitir explicitamente a origem configurada e habilitar credenciais, sem usar `*`. O deploy proposto usa frontend e API no mesmo site para compatibilidade com `SameSite=Lax`. Um deploy entre sites distintos exige revisar cookies e proteção CSRF antes da integração.

Requisições de escrita originadas no navegador devem validar `Origin` contra a origem web permitida; CORS sozinho não substitui essa validação. Cookies, assinaturas e URLs de conexão não devem aparecer em logs.

## 5. Contrato HTTP

Prefixo global: `/api`.

### 5.1 Criar ou substituir o check-in

`PUT /api/check-ins/:date`

```json
{
  "sleep_hours": 7.5,
  "stress_level": 2,
  "mood_level": 1,
  "team_conflict_level": 1,
  "fatigue": 3,
  "description": "Slept well and feel ready for the day."
}
```

Resposta: **200 OK**, tanto para criação quanto para substituição, com o registro completo:

```json
{
  "id": "e14510ab-9d7f-4dc3-b166-10e77900ce21",
  "check_in_date": "2026-11-14",
  "sleep_hours": 7.5,
  "stress_level": 2,
  "mood_level": 1,
  "team_conflict_level": 1,
  "fatigue": 3,
  "description": "Slept well and feel ready for the day.",
  "created_at": "2026-11-14T12:00:00.000Z",
  "updated_at": "2026-11-14T12:00:00.000Z"
}
```

- Os exemplos usam uma data fictícia; a regra de escrita compara a data recebida com o dia atual do backend.
- Persistir por `upsert` usando a chave composta `sessionId_checkInDate`.
- Na atualização, manter `id` e `created_at`; o Prisma atualiza `updated_at` via `@updatedAt`.
- A omissão de `description` em um novo `PUT` remove a descrição anterior, pois a operação substitui o conteúdo completo.
- Repetições não criam duplicatas. Escritas concorrentes para a mesma sessão/data devem resultar em um único registro por meio do `upsert` atômico. O último conteúdo gravado prevalece. Não interpretar códigos de erro do Prisma/PostgreSQL nem implementar retries baseados nesses códigos.

### 5.2 Consultar uma data

`GET /api/check-ins/:date`

- **200 OK:** mesmo formato do registro retornado pelo `PUT`.
- **404 Not Found:** não existe check-in para a data na sessão atual.
- É permitido consultar datas passadas, atuais ou futuras; uma data válida sem registro retorna 404.

### 5.3 Consultar histórico ou intervalo do calendário

`GET /api/check-ins`

Dois modos exclusivos:

| Modo | Exemplo | Comportamento |
| --- | --- | --- |
| Histórico recente | `?limit=7` | Retorna os últimos registros, com data decrescente. Padrão: 7; mínimo: 1; máximo: 90. |
| Calendário | `?from=2026-11-01&to=2026-12-01` | Retorna o intervalo `[from, to)`, com data crescente. Ambas as datas são obrigatórias; `from < to`; máximo de 366 dias. |

Rejeitar `limit` combinado com `from` ou `to`, limites não inteiros, parâmetros desconhecidos e intervalos incompletos. O fim exclusivo deve ser mantido também no contrato do frontend.

Resposta: **200 OK**.

```json
{
  "items": [],
  "today": "2026-11-14",
  "timezone": "UTC"
}
```

Quando houver dados, cada item terá o formato completo de registro definido acima. `today` e `timezone` permitem que o frontend destaque o dia correto sem depender do relógio local. Dias ausentes não geram registros artificiais; lista vazia é sucesso.

### 5.4 Consultar opções das escalas

`GET /api/check-in-options`

Resposta **200 OK**, com os valores lidos das quatro tabelas de opções, ordenados por `value`:

```json
{
  "stress_level": [
    { "value": 1, "label": "Very calm" },
    { "value": 2, "label": "Calm" },
    { "value": 3, "label": "Moderate" },
    { "value": 4, "label": "Stressed" },
    { "value": 5, "label": "Very stressed" }
  ],
  "mood_level": [],
  "team_conflict_level": [],
  "fatigue": []
}
```

O exemplo abrevia três listas; na implementação, elas devem conter todos os valores cadastrados: cinco por dimensão de humor e sete para fadiga.

## 6. Erros

Erros de validação e de negócio definidos pela aplicação usam mensagens em inglês e o seguinte formato:

```json
{
  "statusCode": 400,
  "code": "VALIDATION_ERROR",
  "message": "Invalid check-in data.",
  "details": [
    { "field": "fatigue", "message": "Must be an integer between 1 and 7." }
  ]
}
```

| HTTP | `code` | Situação |
| --- | --- | --- |
| 400 | `VALIDATION_ERROR` | Corpo, data ou consulta inválidos, validados com `class-validator`. |
| 403 | `ORIGIN_NOT_ALLOWED` | Origem de navegador não autorizada para escrita. |
| 404 | `CHECK_IN_NOT_FOUND` | Consulta individual sem registro na sessão. |
| 422 | `CHECK_IN_DATE_NOT_WRITABLE` | Tentativa de gravar fora do dia atual em UTC. |

Não utilizar filtro customizado de exceções nem classificar falhas por códigos do Prisma/PostgreSQL. Verificações de existência devem consultar o banco e avaliar o resultado; por exemplo, consultar o check-in por sessão/data e retornar 404 quando o resultado for `null`.

JSON malformado e exceções inesperadas são tratados pelo mecanismo padrão do NestJS. Falhas inesperadas retornam HTTP 500 com `{ "statusCode": 500, "message": "Internal server error" }`, sem SQL, credenciais ou stack trace na resposta.

## 7. Organização técnica

Estrutura sugerida, consistente com NestJS e TypeScript ESM usados no projeto:

```text
backend/
  src/
    prisma/
      prisma.module.ts
      prisma.service.ts
    session/
      session.module.ts
      session.middleware.ts
    check-ins/
      check-ins.module.ts
      check-ins.controller.ts
      check-in-options.controller.ts
      check-ins.service.ts
      dto/
        check-in-date.input.ts
        put-check-in.input.ts
        list-check-ins.input.ts
        check-in.output.ts
        list-check-ins.output.ts
        check-in-options.output.ts
      requests/
        put-check-in.request.ts
      query-params/
        list-check-ins.query-params.ts
        check-in-date-range.validator.ts
      path-params/
        check-in.path-params.ts
      check-in.presenter.ts
  test/
    check-ins.e2e-spec.ts
```

- Configurar o prefixo `/api`, validação e CORS, utilizando o tratamento padrão de exceções do NestJS.
- Usar interfaces sem validações em `dto/`, com arquivos `.input.ts` e `.output.ts`, para os contratos dos services. Validar corpo, query e path com `class-validator` nas classes de `requests/`, `query-params/` e `path-params/`, respectivamente. Aplicar `ValidationPipe` e usar `class-transformer` apenas para a conversão do limite da query e a normalização da descrição. Converter datas para o Prisma no service, sem parsers manuais de validação.
- Usar uma instância compartilhada de `PrismaService`, com encerramento adequado da conexão.
- Instalar e fixar versões compatíveis do Prisma CLI e client. O schema atual usa `url = env("DATABASE_URL")`, formato validado com Prisma 6; uma atualização de major exige ajustar a configuração correspondente.
- Padronizar a conexão em `DATABASE_URL`, conforme o datasource Prisma. Se o ambiente ainda usar `DATASOURCE_URL`, alinhar o nome no setup sem expor o valor.
- Configurar `SESSION_SECRET`, `WEB_ORIGIN`, `PORT` e ambiente de execução no servidor. Carregar a configuração antes de instanciar o Prisma.
- Usar o pooler adequado à execução da aplicação; comandos de migração/diff devem usar conexão direta ou pooler em modo sessão, conforme disponibilidade de rede.
- Nenhuma nova tabela é necessária para este recorte. Preservar as restrições SQL de faixa, chaves estrangeiras e RLS existentes.
- O acesso será exclusivamente pelo backend. O RLS existente não identifica sessões de demonstração; o isolamento por sessão deve ser implementado explicitamente em cada operação do backend.

## 8. Critérios de aceite e testes

- [x] Primeira consulta estabelece cookie; consultas seguintes reutilizam a sessão.
- [x] Cookie adulterado ou expirado estabelece nova sessão e não recupera o histórico anterior.
- [x] Salvar check-in válido retorna todos os campos no formato especificado.
- [x] Reenviar a mesma sessão/data mantém um registro, preserva `id` e `created_at` e atualiza os indicadores.
- [x] Escritas concorrentes não criam duplicatas nem produzem erro de conflito não tratado.
- [x] `description` é normalizada e removida quando omitida em uma substituição.
- [x] Valores limite válidos são aceitos; números fora de faixa, frações nas escalas, strings numéricas, campos desconhecidos e indicadores ausentes são rejeitados.
- [x] Datas inexistentes e consultas inválidas são rejeitadas.
- [x] Com relógio controlado, gravações em datas passadas/futuras são rejeitadas; o dia atual é calculado em UTC mesmo perto da meia-noite.
- [x] Histórico recente respeita limite e ordenação; calendário inclui `from` e exclui `to`.
- [x] Sessão B não lê nem altera os registros da sessão A, incluindo ao consultar a mesma data.
- [ ] Recarregar o cliente mantém os dados enquanto o cookie é válido.
- [x] Opções retornam 5/5/5/7 valores ordenados, com rótulos em inglês vindos do banco.
- [x] Erro de banco retorna resposta sanitizada; escrita de origem não autorizada é rejeitada.
- [x] Build, lint e testes relevantes passam.

Usar Vitest/Supertest para HTTP e cookies. Os testes de persistência devem rodar em um banco de teste isolado e comprovar upsert, concorrência e isolamento por sessão; mocks sozinhos não comprovam essas propriedades. Executar também os [testes SQL existentes](../../backend/test/database/check-ins.sql) para verificar as restrições. Não apagar registros de outras sessões durante limpeza de testes.

Implementação e comandos de execução: [README do backend](../../backend/README.md). A verificação automatizada cobre a API com PostgreSQL local e a reutilização de cookies entre requisições; a validação da interface em navegador ocorre na integração do frontend.

## 9. Sequência de implementação

1. Configurar Prisma, conexão e variáveis de ambiente; gerar o client.
2. Implementar sessão e validação de configuração.
3. Implementar validações, gravação por upsert, serialização e consulta individual.
4. Implementar listagem por limite/intervalo e leitura de opções.
5. Padronizar erros e executar os testes de aceite.
6. Integrar o frontend: carregar opções e calendário, enviar `PUT` e refazer a consulta após sucesso.

O resultado esperado desta SPEC é uma API persistente e integrável ao calendário. Previsão de fadiga, geração de insights e processamento de ações terão contratos próprios em etapas posteriores.

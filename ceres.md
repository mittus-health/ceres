# Ceres — IA de recomendação e checklist

Documento de integração do Ceres com o backend do Mittus. Para rodar e configurar, veja o [README](README.md). Para o escopo da feature, veja a linha "Recomendação e checklist gerados pela IA" em [FEATURES.md](FEATURES.md).

## O que o Ceres faz

Uma vez por dia, depois que o astronauta salva o check-in, o Ceres produz duas coisas, em inglês:

1. **O card** de **Make sense of the changes**: um título, um resumo do que mudou e uma próxima etapa.
2. **As tarefas** da IA para o checklist **My plan**: no máximo duas, uma baseada no check-in e uma baseada no resultado do Eres.

Ele **não acessa o banco, não chama o Eres e não guarda nada**. O backend envia os dados, recebe o resultado e grava.

```
Front --salva check-in--> Backend (NestJS) --Eres--> previsão
                              |
                              |  POST /v1/recommendations
                              |  { check_ins, forecast }
                              v
                           Ceres (FastAPI) ----> Command Code (modelo de linguagem)
                              |
                              |  { insight, tasks }
                              v
                    Backend grava check_in_insights e check_in_actions
```

### O que é código e o que é modelo

| Responsabilidade | Quem faz |
| --- | --- |
| Comparar o último check-in com a média de até 7 anteriores (sem o registro atual) | **Código** |
| Decidir quais tarefas existem, o `action_code` e o `reason_code` | **Código** (regras versionadas) |
| Escrever o título e o resumo do card, a próxima etapa e os títulos das tarefas | **Modelo** |
| Escolher, criar ou remover tarefas; dar conselho médico; sugerir contato com a equipe médica | **Ninguém no Ceres.** `contact_crew` e `contact_medical` nunca saem daqui |

Se o modelo falhar, demorar mais de 45 s ou devolver algo fora dos limites, o Ceres responde com **texto determinístico** que usa os mesmos números. O campo `insight.source` diz `ai` ou `fallback`. O contrato da resposta é idêntico nos dois casos.

## Stack

| Parte | Tecnologia |
| --- | --- |
| Linguagem e servidor | Python 3.12 ou mais novo (testado na 3.14), FastAPI, uvicorn |
| Contratos e validação | Pydantic v2 (campos extras e números em string são rejeitados) |
| Modelo de linguagem | **Command Code**, API compatível com OpenAI (`POST {base_url}/chat/completions`), modelo `deepseek/deepseek-v4-pro` |
| Cliente HTTP | httpx, com o repositório de certificados do sistema (`truststore`) |
| Configuração | Variáveis de ambiente e `.env` (`python-dotenv`) |
| Testes | pytest e pytest-asyncio, 63 testes, sem chamadas de rede |

## Arquitetura

Camadas com dependências que apontam sempre para dentro: `api` e `infrastructure` dependem de `application`, que depende de `domain`. O `domain` não importa FastAPI, Pydantic nem httpx.

```
app/
  domain/            regras e dados, sem framework nem I/O
    entities.py        CheckIn, Facts, TaskSpec, Task, Insight, GeneratedText...
    facts.py           FactsCalculator: último check-in contra a média dos anteriores
    task_policies.py   TaskPolicy, CheckInFollowUpPolicy, ForecastFollowUpPolicy, TaskPlanner
  application/       casos de uso e portas
    ports.py           TextWriter, ChatModel (interfaces)
    build_recommendation.py   BuildRecommendation: o caso de uso
    writers.py         TemplateTextWriter (texto de reserva), GuardedTextWriter (timeout, validação, reserva)
    text_validation.py TextLimits, TextValidator
  infrastructure/    adaptadores para o mundo externo
    llm/commandcode_chat_model.py   ChatModel sobre HTTP (só transporte)
    llm/prompt.py                   o prompt
    llm/llm_text_writer.py          TextWriter sobre qualquer ChatModel (monta o prompt, lê o JSON)
    settings.py                     Settings.from_env
  api/               HTTP
    schemas.py         contrato Pydantic e mapeamento para o domínio
    routes.py          rotas finas
  container.py       raiz de composição: o único lugar que escolhe as classes concretas
  main.py            create_app(settings, use_case)
```


## Contrato da integração

### `POST /v1/recommendations`

**Requisição**

```json
{
  "check_ins": [
    { "id": "4f6c…", "check_in_date": "2026-11-13", "sleep_hours": 6.7,
      "stress_level": 2, "mood_level": 2, "team_conflict_level": 1, "fatigue": 3 },
    { "id": "9ab1…", "check_in_date": "2026-11-14", "sleep_hours": 6.5,
      "stress_level": 2, "mood_level": 2, "team_conflict_level": 1, "fatigue": 5 }
  ],
  "forecast": {
    "status": "ready",
    "probability_high_fatigue": 0.38,
    "model_version": "eres-v2",
    "predicted_at": "2026-11-14T12:00:00.000Z"
  }
}
```

| Campo | Regra |
| --- | --- |
| `check_ins` | De 1 a 90 itens, **do mais antigo ao mais recente**, uma por data. **O último é o check-in de hoje**. Enviar o histórico completo da sessão; o Ceres usa só os 7 anteriores ao último. |
| `check_ins[].id` | O `id` do registro em `check_ins`. Volta em `insight.facts.check_in_id`. |
| `check_ins[].check_in_date` | `YYYY-MM-DD`. |
| `sleep_hours` | Número de 0 a 24. |
| `stress_level`, `mood_level`, `team_conflict_level` | Inteiros de 1 a 5. |
| `fatigue` | Inteiro de 1 a 7. |
| `forecast` | **Opcional.** `ready` (com os três campos do Eres), `insufficient_history` ou `unavailable`. Ausente, `insufficient_history` e `unavailable` significam "sem tarefa do Eres": o card e a tarefa do check-in saem só com os check-ins. |

**Não enviar** `description`, `session_id`, `created_at` nem `updated_at`. **Qualquer campo extra devolve `422`.** Isso garante que texto livre do astronauta e identificadores da sessão nunca cheguem ao modelo. Números como string (`"7"`) também são rejeitados.

**Resposta `200`**

```json
{
  "insight": {
    "title": "Sleep slightly below average and fatigue above average",
    "summary": "Your latest check-in shows 6.5 hours of sleep, 0.2 hours below your average of 6.7 hours. Fatigue is 5, 1.5 points above your average of 3.5. The experimental model estimates a 38% probability of high fatigue at the next check-in.",
    "next_step": "At your next check-in, record your sleep hours and fatigue again to see if the change persists.",
    "facts": {
      "check_in_id": "9ab1…",
      "check_in_date": "2026-11-14",
      "comparison": "available",
      "compared_check_ins": 6,
      "indicators": {
        "sleep_hours": { "current": 6.5, "baseline_mean": 6.7, "delta": -0.2, "direction": "down" },
        "fatigue": { "current": 5, "baseline_mean": 3.5, "delta": 1.5, "direction": "up" },
        "mood_level": { "current": 2, "baseline_mean": 2.0, "delta": 0.0, "direction": "same" },
        "stress_level": { "current": 2, "baseline_mean": 2.0, "delta": 0.0, "direction": "same" },
        "team_conflict_level": { "current": 1, "baseline_mean": 1.0, "delta": 0.0, "direction": "same" }
      },
      "forecast": { "probability_high_fatigue": 0.38, "model_version": "eres-v2" }
    },
    "source": "ai",
    "generator": "commandcode:deepseek/deepseek-v4-pro"
  },
  "tasks": [
    {
      "task_key": "check_in_follow_up",
      "title": "Record a new check-in",
      "source": "check_in",
      "kind": "task",
      "action_code": "recheck",
      "reason_code": "check_in_sleep_or_fatigue_worsened",
      "ruleset_version": "ceres-check-in-v1",
      "status": "suggested",
      "forecast_snapshot": null
    },
    {
      "task_key": "forecast_follow_up",
      "title": "Keep tracking your fatigue",
      "source": "forecast",
      "kind": "task",
      "action_code": "monitor",
      "reason_code": "forecast_below_demo_threshold",
      "ruleset_version": "demo-follow-up-v1",
      "status": "suggested",
      "forecast_snapshot": {
        "probability_high_fatigue": 0.38,
        "model_version": "eres-v2",
        "predicted_at": "2026-11-14T12:00:00.000Z"
      }
    }
  ]
}
```

- Com um único check-in, `facts.comparison` é `no_history` e `baseline_mean`, `delta` e `direction` são `null`.
- `source` é `fallback` e `generator` é `null` quando o texto vem da reserva.
- Os textos têm limites: título até 80 caracteres, resumo até 400, `next_step` até 200 e título de tarefa até 100.

**Erros**

| HTTP | Quando |
| --- | --- |
| `422` | Corpo inválido: histórico vazio ou fora de ordem, data repetida, valor fora da faixa, campo extra, status de previsão desconhecido. A lista de problemas vem no corpo, no formato padrão do FastAPI (`detail`). |
| `500` | Erro inesperado. Falha do provedor de IA **não** vira erro: vira `source: "fallback"` com `200`. |

### `GET /health`

Responde `{"status": "ok"}`. Serve para o deploy verificar que o serviço subiu.

## Tarefas que o Ceres devolve

| `task_key` | `source` | Quando existe | `action_code` |
| --- | --- | --- | --- |
| `check_in_follow_up` | `check_in` | Sempre | `recheck` se o sono ficou 1 h ou mais abaixo da média, ou a fadiga 1 ponto ou mais acima; senão `monitor` |
| `forecast_follow_up` | `forecast` | Só com `forecast.status = "ready"` | `recheck` com probabilidade ≥ 0,5; senão `monitor` (regra `demo-follow-up-v1`, a mesma do Check-in Actions) |

Os limiares são para a demonstração com dados sintéticos. Não são limiares clínicos.

As tarefas fixas da tela do checklist, **Save today's check-in** (já concluída) e **Review the check-in insight** (abre o card), **não são geradas pelo Ceres**. O backend as cria sem IA.

## O que o backend precisa fazer

**Quando chamar.** No `POST /api/check-ins/{id}/actions/evaluate`, depois de obter o resultado do Eres e antes de gravar. Só para o check-in mais recente da sessão, como já é hoje.

**Montar a requisição.** Histórico completo da sessão em ordem cronológica (o mesmo que vai ao Eres), apenas com os sete campos do check-in, e o resultado do Eres adaptado (`ok` vira `ready`).

**Gravar o resultado** na mesma transação que marca as anteriores como `superseded`:

| Resposta do Ceres | Onde grava |
| --- | --- |
| `insight.title`, `summary`, `facts`, `source`, `generator` | `check_in_insights` (colunas de mesmo nome). `check_in_id` e `evaluation_key` vêm do backend. |
| `insight.next_step` | **Ainda sem coluna** (veja "Pontos em aberto"). |
| `tasks[]` | Uma linha de `check_in_actions` por tarefa: `task_key`, `title`, `source`, `kind`, `action_code`, `reason_code`, `ruleset_version`, `status`, `forecast_snapshot`. A chave única é `(check_in_id, evaluation_key, task_key)`. |
| Tarefas fixas | O backend insere `save_check_in` (`source: system`, `status: completed`) e `review_insight` (`kind: review_insight`) sem passar pelo Ceres. |

O `evaluation_key` é do backend, e o Ceres não o conhece.

**Idempotência e custo.** Chame o Ceres **só quando a avaliação é nova**. Repetir a mesma avaliação reaproveita as linhas já gravadas e não chama o Ceres de novo. Uma correção dos indicadores muda o `evaluation_key`, então gera um novo card e novas tarefas, e os anteriores ficam `superseded` (`check_in_insights.superseded_at`). Edição só da descrição não deve chamar o Ceres.

**Timeout e falhas.**
- O Ceres espera até **45 s** pelo modelo. Medido: 6 a 23 s na maioria das chamadas, com picos de até 45 s. O cliente do backend precisa de um timeout **maior que 45 s** (sugestão: 60 s).
- O front não deve ficar bloqueado nesse tempo. Salve o check-in primeiro e mostre o cartão como "preparando" até a avaliação terminar.
- Se o próprio Ceres estiver fora do ar (timeout de conexão ou `5xx`), o backend não grava card nem tarefas da IA, mantém o check-in salvo e pode tentar de novo na próxima avaliação. O check-in nunca depende do Ceres.

## Configuração

Variáveis do processo do Ceres (arquivo `.env`, que o Git ignora; a chave é segredo do servidor):

| Variável | Uso |
| --- | --- |
| `COMMANDCODE_API_KEY` | Chave da API do Command Code. |
| `COMMANDCODE_BASE_URL` | `https://api.commandcode.ai/provider/v1` |
| `COMMANDCODE_MODEL` | `deepseek/deepseek-v4-pro` |
| `CERES_GENERATOR_TIMEOUT_SECONDS` | Opcional. Padrão 45. |

Sem as três primeiras, o Ceres funciona só com o texto de reserva.

**Rodar:**

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"    # Linux/macOS: .venv/bin/python
.venv/Scripts/python -m uvicorn app.main:app --env-file .env --port 8000
.venv/Scripts/python -m pytest
```

**Deploy (Neves).** É um processo único e sem estado, então pode ter várias instâncias. Precisa das variáveis acima e de acesso HTTPS de saída ao `api.commandcode.ai`. O Ceres **não tem autenticação**: deve ficar numa rede interna, acessível só pelo backend, e não ser exposto ao navegador.

## Qualidade e testes

- 63 testes automáticos, organizados por camada em `tests/domain`, `tests/application`, `tests/infrastructure` e `tests/api`. Cobrem: a comparação (janela de 7, exclusão do registro atual, histórico único), as regras e os limiares das tarefas, o texto de reserva e o guarda (erro, timeout, saída inválida), o cliente HTTP e o escritor do modelo com respostas simuladas (sucesso, JSON com cerca de código, erro 401 e 500, JSON inválido, campos faltando), a validação das entradas e o `422` para `description` e `session_id`.
- Verificação com o provedor real (dados simulados, seis cenários: piora com previsão baixa e alta, estável, melhora, primeiro check-in e Eres indisponível): todos voltaram com `source: "ai"`, e todos os números do texto conferem com os `facts`. Latência de 7 a 16 s nessa rodada. Em uma rodada anterior, um caso passou de 45 s e usou o texto de reserva, como previsto.
- O modelo raciocina antes de responder, e testamos parâmetros para limitar isso: nenhum reduziu a latência de forma útil.

## Uso de IA (para a submissão)

Subsídio para o campo **Use of Super Intelligence (SI)** da aba Project:

- Um modelo de linguagem (`deepseek/deepseek-v4-pro`, via Command Code) **escreve em inglês** o título, o resumo e a próxima etapa do card e os títulos das duas tarefas da IA do checklist.
- O modelo recebe só números simulados já calculados (valores dos indicadores, médias e diferenças, e a probabilidade do Eres). Não recebe a descrição escrita pelo astronauta nem identificadores.
- O modelo **não decide** quais tarefas existem, nem a ação sugerida, e não dá conselho médico. Isso é feito por regras versionadas no código.
- Todos os dados da demonstração são simulados. A previsão do Eres é experimental e treinada com dados sintéticos.
- Se o modelo falhar, o app mostra um texto gerado por regras com os mesmos números, e o campo `source` registra qual foi usado.

## Pontos em aberto

1. **`next_step`**: o card tem uma terceira linha (a próxima etapa), mas `check_in_insights` não tem coluna para ela. Opções: nova coluna `next_step`, ou concatenar ao `summary`.
2. **Prisma do backend**: o schema precisa dos campos novos de `check_in_actions` (`task_key`, `title`, `source`, `kind`, `forecast_snapshot` opcional), da nova chave única e do modelo `check_in_insights`. O código atual do Check-in Actions insere ações sem `task_key`, `title`, `source` e `kind` e vai falhar no banco compartilhado até ser atualizado.
3. **Autenticação entre o backend e o Ceres**: hoje não existe. Se o Ceres sair da rede interna, é preciso um segredo compartilhado.
4. **Tarefas fixas**: confirmar que `save_check_in` e `review_insight` ficam com o backend e não com o Ceres.
5. **Chave da API**: foi compartilhada em texto durante o desenvolvimento. Trocá-la antes de publicar.

## Banco

Migrações já aplicadas no Supabase do projeto, em [supabase/migrations](supabase/migrations):

- `20261115000000_create_check_in_insights.sql`: cria `public.check_in_insights`, com RLS ligado e sem acesso para `anon` e `authenticated`. Um índice único parcial garante no máximo um insight vigente por check-in.
- `20261115000100_check_in_actions_as_tasks.sql`: faz cada linha de `check_in_actions` ser uma tarefa (`task_key`, `title`, `source`, `kind`, `forecast_snapshot` opcional e nova chave única). As 1114 linhas existentes foram migradas.

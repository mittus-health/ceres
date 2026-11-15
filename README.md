# Ceres

Serviço FastAPI da IA do Mittus: gera o **card diário** ("Make sense of the changes") e as **tarefas do checklist** a partir dos check-ins e do resultado do Eres. Escopo em [FEATURES.md](FEATURES.md#funcionalidades-e-dependências) (linha "Recomendação e checklist gerados pela IA").

O Ceres **não tem estado e não acessa o banco**. O backend envia os dados, o Ceres responde, e o backend grava em `check_in_insights` e `check_in_actions`.

```
backend (NestJS) --POST /v1/recommendations--> Ceres
   check_ins da sessão + resultado do Eres        |
backend <------ insight + tasks -----------------+
   grava check_in_insights e check_in_actions
```

## O que é código e o que é modelo

- **Código:** os números (último check-in contra a média de até 7 anteriores, sem o registro atual) e **quais tarefas existem**, com `action_code`, `reason_code` e regra. O modelo nunca escolhe nem cria tarefas.
- **Modelo de linguagem:** só redige o título, o resumo e a próxima etapa do card e os títulos das tarefas. O provedor é o **Command Code** (API compatível com OpenAI, modelo `deepseek/deepseek-v4-pro`). O modelo raciocina antes de responder, então a chamada leva de 7 a 20 s. A estrutura do código está em [ceres.md](ceres.md#arquitetura).
- **Texto de reserva:** sem gerador, ou se ele falhar, demorar mais que 8 s ou devolver algo inválido, o Ceres usa texto determinístico com os mesmos números. `insight.source` diz `ai` ou `fallback`.

## Tarefas devolvidas

| `task_key` | Origem | Quando |
| --- | --- | --- |
| `check_in_follow_up` | `check_in` | Sempre. `recheck` se o sono caiu 1 h ou mais, ou a fadiga subiu 1 ponto ou mais, contra a média; senão `monitor`. |
| `forecast_follow_up` | `forecast` | Só se o Eres devolveu `ready`. `recheck` com probabilidade ≥ 0,5 (regra `demo-follow-up-v1`, a mesma do Check-in Actions), senão `monitor`. |

Sem resultado do Eres (ausente, `insufficient_history` ou `unavailable`), o card e a tarefa do check-in continuam saindo só com os check-ins. Os limiares são da demonstração com dados sintéticos e não são clínicos. O Ceres não gera `contact_crew` nem `contact_medical`.

As tarefas fixas da tela (**Save today's check-in** e **Review the check-in insight**) não são da IA e ficam com o backend.

## API

`POST /v1/recommendations`

```json
{
  "check_ins": [
    { "id": "…", "check_in_date": "2026-11-13", "sleep_hours": 6.7, "stress_level": 2,
      "mood_level": 2, "team_conflict_level": 1, "fatigue": 3 },
    { "id": "…", "check_in_date": "2026-11-14", "sleep_hours": 6.5, "stress_level": 2,
      "mood_level": 2, "team_conflict_level": 1, "fatigue": 5 }
  ],
  "forecast": { "status": "ready", "probability_high_fatigue": 0.38,
                "model_version": "eres-v2", "predicted_at": "2026-11-14T12:00:00.000Z" }
}
```

- `check_ins`: de 1 a 90, **do mais antigo ao mais recente**, uma por data; o último é o de hoje. Sem `description`, `session_id` ou timestamps: campos extras são rejeitados com `422`, e números em string também.
- `forecast`: opcional. Aceita `ready`, `insufficient_history` ou `unavailable`.

Resposta: `insight` (`title`, `summary`, `next_step`, `facts`, `source`, `generator`) e `tasks` (`task_key`, `title`, `source`, `kind`, `action_code`, `reason_code`, `ruleset_version`, `status`, `forecast_snapshot`). `insight` corresponde a uma linha de `check_in_insights` e cada item de `tasks` a uma de `check_in_actions` ([migrações](supabase/migrations)). Quem calcula o `evaluation_key` é o backend.

`GET /health` responde `{"status": "ok"}`.

## Configuração

Variáveis de ambiente (arquivo `.env`, que o Git ignora; a chave é segredo do servidor):

| Variável | Uso |
| --- | --- |
| `COMMANDCODE_API_KEY` | Chave da API. |
| `COMMANDCODE_BASE_URL` | Por exemplo `https://api.commandcode.ai/provider/v1`. |
| `COMMANDCODE_MODEL` | Por exemplo `deepseek/deepseek-v4-pro`. |
| `CERES_GENERATOR_TIMEOUT_SECONDS` | Opcional. Tempo máximo do provedor antes do texto de reserva; padrão 45. |

Sem as três primeiras, o Ceres roda só com o texto de reserva. As chamadas ao provedor usam o repositório de certificados do sistema (`truststore`), para funcionar em redes que inspecionam HTTPS.

## Rodar

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"   # Linux/macOS: .venv/bin/python
.venv/Scripts/python -m uvicorn app.main:app --env-file .env --port 8000
.venv/Scripts/python -m pytest
```

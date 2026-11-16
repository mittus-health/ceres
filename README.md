<div align="center">

<img src="assets/logo.png" alt="Mittus logo" width="280" />

# Ceres

### The AI recommendation service of [Mittus](https://github.com/mittus-health/mittus-astronaut-health)

Insight card · checklist tasks · deterministic fallback

[![NASA Space Apps 2026](https://img.shields.io/badge/NASA%20Space%20Apps-2026-0B3D91?style=for-the-badge)](https://www.spaceappschallenge.org/2026/challenges/health-monitoring-software/?tab=details)

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-E92063?style=flat-square&logo=pydantic&logoColor=white)
![Tests](https://img.shields.io/badge/tests-63%20passing-2EA44F?style=flat-square)

</div>

---

## About

Ceres is the AI service behind [Mittus](https://www.spaceappschallenge.org/2026/challenges/health-monitoring-software/?tab=details), our entry for the **NASA Space Apps Challenge 2026** ("Create Health Monitoring Software for Astronauts on Space Missions"). Once a day, after the astronaut saves a check-in, Ceres produces:

1. **The insight card** shown in **Make sense of the changes**: a title, a summary of what changed and a next step.
2. **Up to two checklist tasks** for **My plan**: one based on the check-in and one based on the Eres fatigue forecast.

Everything is written in English. All demo data is simulated, and the Eres forecast is experimental (trained on synthetic data). Nothing here is medical advice.

Ceres is **stateless**. It does not access the database, does not call Eres and stores nothing. The backend sends the data, Ceres answers, and the backend persists the result.

```
Front --saves check-in--> Backend (NestJS) --Eres--> forecast
                              |
                              |  POST /v1/recommendations
                              |  { check_ins, forecast }
                              v
                           Ceres (FastAPI) ----> Command Code (language model)
                              |
                              |  { insight, tasks }
                              v
                Backend writes check_in_insights and check_in_actions
```

## What is code and what is the model

| Responsibility | Who does it |
| --- | --- |
| Compare the latest check-in with the mean of up to 7 previous ones (current record excluded) | **Code** |
| Decide which tasks exist, plus `action_code` and `reason_code` | **Code** (versioned rules) |
| Write the card title, summary, next step and task titles | **Language model** |
| Pick, create or remove tasks; give medical advice; suggest contacting crew or medical staff | **Nobody in Ceres.** `contact_crew` and `contact_medical` are never emitted here |

If the model is not configured, fails, exceeds the timeout (45 s by default) or returns text outside the limits, Ceres answers with **deterministic fallback text** built from the same numbers. `insight.source` is `ai` or `fallback`; the response contract is identical in both cases.

The model only receives numbers that were already computed (indicator values, means, deltas and the Eres probability). It never receives the astronaut's free-text description or any identifier.

## Tasks returned

| `task_key` | Source | When it exists |
| --- | --- | --- |
| `check_in_follow_up` | `check_in` | Always. `recheck` if sleep is 1 h or more below the mean, or fatigue is 1 point or more above it; otherwise `monitor`. |
| `forecast_follow_up` | `forecast` | Only when Eres returned `ready`. `recheck` at probability ≥ 0.5 (rule `demo-follow-up-v1`, the same as Check-in Actions); otherwise `monitor`. |

Without an Eres result (absent, `insufficient_history` or `unavailable`) the card and the check-in task are still produced from the check-ins alone. Thresholds are for the demo with synthetic data and are **not clinical thresholds**.

The two fixed checklist tasks, **Save today's check-in** and **Review the check-in insight**, are not AI-generated; the backend creates them.

## API

### `POST /v1/recommendations`

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

| Field | Rule |
| --- | --- |
| `check_ins` | 1 to 90 items, **oldest to newest**, one per date. The last one is today's check-in. |
| `sleep_hours` | Number from 0 to 24. |
| `stress_level`, `mood_level`, `team_conflict_level` | Integers from 1 to 5. |
| `fatigue` | Integer from 1 to 7. |
| `forecast` | Optional. `ready` (with `probability_high_fatigue`, `model_version`, `predicted_at`), `insufficient_history` or `unavailable`. |

Do not send `description`, `session_id` or timestamps: **extra fields are rejected with `422`**, and so are numbers sent as strings.

The `200` response has:

- `insight`: `title`, `summary`, `next_step`, `facts`, `source`, `generator`. Title ≤ 80 characters, summary ≤ 400, next step ≤ 200.
- `tasks`: each with `task_key`, `title` (≤ 100), `source`, `kind`, `action_code`, `reason_code`, `ruleset_version`, `status` and `forecast_snapshot`.

With a single check-in, `facts.comparison` is `no_history` and the baseline fields are `null`. A model failure is never an error: it becomes `source: "fallback"` with HTTP `200`. Invalid bodies return `422`; unexpected errors return `500`.

The full contract, examples and backend integration notes are in [ceres.md](ceres.md).

### `GET /health`

Returns `{"status": "ok"}`.

## Architecture

Dependencies always point inward: `api` and `infrastructure` depend on `application`, which depends on `domain`. The domain imports no framework.

```
app/
  domain/          entities, facts calculation, task policies (no I/O)
  application/     BuildRecommendation use case, ports, text writers, validation
  infrastructure/  Command Code client, prompt, LLM text writer, settings
  api/             FastAPI routes and Pydantic schemas
  container.py     composition root
  main.py          create_app
```

## Configuration

Environment variables, read from the process or from a `.env` file (ignored by Git; the key is a server secret):

| Variable | Use |
| --- | --- |
| `COMMANDCODE_API_KEY` | Command Code API key. |
| `COMMANDCODE_BASE_URL` | OpenAI-compatible base URL, e.g. `https://api.commandcode.ai/provider/v1`. |
| `COMMANDCODE_MODEL` | Model name, e.g. `deepseek/deepseek-v4-pro`. |
| `CERES_GENERATOR_TIMEOUT_SECONDS` | Optional. Provider timeout before falling back. Default 45. |

Without the first three, Ceres runs on fallback text only. Provider calls use the system certificate store (`truststore`) so they work behind HTTPS-inspecting networks.

## Run

Requires Python 3.12 or newer.

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"   # Linux/macOS: .venv/bin/python
.venv/Scripts/python -m uvicorn app.main:app --env-file .env --port 8000
```

Run the tests (no network calls):

```bash
.venv/Scripts/python -m pytest
```

## Deployment notes

- Single stateless process; several instances are fine.
- The language model can take 6 to 23 s, with peaks up to the 45 s timeout. The backend's HTTP client needs a timeout **above 45 s** (60 s suggested), and the front end should not block on it.
- Ceres has **no authentication**. Keep it on an internal network reachable only by the backend, never from the browser.

## Use of AI (for the submission)

- A language model (`deepseek/deepseek-v4-pro` through Command Code) writes the card title, summary and next step and the titles of the two AI tasks.
- It does not decide which tasks exist or which action is suggested, and it gives no medical advice. Versioned rules in code do that.
- Inputs are simulated numbers only. The Eres forecast is experimental and was trained on synthetic data.
- On any failure the app shows rule-generated text with the same numbers, and `source` records which one was used.

## Related

- [FEATURES.md](FEATURES.md) — MVP features, routes and database
- [ceres.md](ceres.md) — integration contract with the Mittus backend
- [REQUISITOS-DE-ENTREGA.md](REQUISITOS-DE-ENTREGA.md) — submission requirements
- [Database migrations](supabase/migrations)

## Team

<table align="center">
  <tr>
    <td align="center" width="170">
      <a href="https://github.com/luismede">
        <img src="https://github.com/luismede.png?size=200" width="100" alt="@luismede" /><br />
        <sub><b>@luismede</b></sub>
      </a><br />
      <sub>Daily check-in backend</sub>
    </td>
    <td align="center" width="170">
      <a href="https://github.com/Neveslv">
        <img src="https://github.com/Neveslv.png?size=200" width="100" alt="@Neveslv" /><br />
        <sub><b>@Neveslv</b></sub>
      </a><br />
      <sub>Check-in Actions and deploy</sub>
    </td>
    <td align="center" width="170">
      <a href="https://github.com/luibiondo">
        <img src="https://github.com/luibiondo.png?size=200" width="100" alt="@luibiondo" /><br />
        <sub><b>@luibiondo</b></sub>
      </a><br />
      <sub>Frontend</sub>
    </td>
  </tr>
  <tr>
    <td align="center" width="170">
      <a href="https://github.com/RodrigoBolgheroni">
        <img src="https://github.com/RodrigoBolgheroni.png?size=200" width="100" alt="@RodrigoBolgheroni" /><br />
        <sub><b>@RodrigoBolgheroni</b></sub>
      </a><br />
      <sub>Machine Learning (Eres)</sub>
    </td>
    <td align="center" width="170">
      <a href="https://github.com/giumanara">
        <img src="https://github.com/giumanara.png?size=200" width="100" alt="@giumanara" /><br />
        <sub><b>@giumanara</b></sub>
      </a><br />
      <sub>AI recommendation (Ceres)</sub>
    </td>
    <td align="center" width="170">
      <a href="https://github.com/gabkbenfica">
        <img src="https://github.com/gabkbenfica.png?size=200" width="100" alt="@gabkbenfica" /><br />
        <sub><b>@gabkbenfica</b></sub>
      </a><br />
      <sub>Design</sub>
    </td>
  </tr>
</table>

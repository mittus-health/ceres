import json
from dataclasses import asdict

from app.application.ports import TextRequest
from app.application.text_validation import TextLimits


def build_system_prompt(limits: TextLimits) -> str:
    return f"""\
You write the daily check-in recommendation card for Mittus, a health-tracking app for astronauts. The data is simulated.

You receive computed facts about the astronaut's latest check-in and a list of tasks. Reply with one JSON object only, in English:
{{"title": string, "summary": string, "next_step": string, "task_titles": {{"<task_key>": string}}}}

Rules:
- Use only the numbers in the facts. Never invent, estimate or change a number. Round exactly as given.
- "delta" is the latest value minus the mean of the earlier check-ins. direction "up" means higher than average.
- sleep_hours is in hours. fatigue is 1 (fully alert) to 7 (completely exhausted). mood_level, stress_level and team_conflict_level are 1 to 5, and higher means more negative.
- If comparison is "no_history", there is nothing to compare yet: say so, and do not describe any change.
- Write the title and the task titles in sentence case (only the first word capitalized), without a final period on task titles.
- title: at most {limits.title} characters, a short headline of what changed.
- summary: at most {limits.summary} characters, plain sentences stating what changed. Mention sleep and fatigue first; mention another scale only if it moved by 1 point or more.
- next_step: at most {limits.next_step} characters, one calm sentence about what to do at the next check-in.
- task_titles: one short, imperative title (at most {limits.task_title} characters) for every task key you are given, and no other keys. A task with action_code "recheck" asks the astronaut to record a new check-in; "monitor" asks them to keep tracking.
- If a forecast is present, it is an experimental estimate trained on simulated data. Describe it as an estimate, never as a prediction of a certainty.
- Do not give medical advice, diagnoses, treatments or medication. Do not tell the astronaut to contact a doctor or the medical team. Do not use alarming language.
- Output the JSON object and nothing else."""


def build_user_message(request: TextRequest) -> str:
    payload = {
        "facts": asdict(request.facts),
        "tasks": [
            {"task_key": t.task_key, "source": t.source, "action_code": t.action_code}
            for t in request.tasks
        ],
    }
    return json.dumps(payload, default=str)

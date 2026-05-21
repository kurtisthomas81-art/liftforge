import json


def epley_1rm(weight: float, reps: int) -> float:
    if reps == 1:
        return weight
    return weight * (1 + reps / 30.0)


def parse_muscle_list(raw) -> list[str]:
    if isinstance(raw, list):
        return raw
    if not raw:
        return []
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []

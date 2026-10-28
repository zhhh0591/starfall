"""Choose a daytime fanart slot after a randomly spaced interval."""
from datetime import datetime, timedelta
import random
import time


def next_post_time(config: dict, now: float | None = None) -> float:
    now = time.time() if now is None else now
    minimum = float(config["image_interval_min_hours"])
    maximum = float(config["image_interval_max_hours"])
    due = datetime.fromtimestamp(now + random.uniform(minimum, maximum) * 3600)
    slots = []
    start, end = int(config["image_start_hour"]), int(config["image_end_hour"])
    for raw in config.get("fanart_schedule_times", ["12:30", "18:30"]):
        try:
            hour, minute = map(int, raw.split(":"))
            if start <= hour < end and 0 <= minute < 60:
                slots.append((hour, minute))
        except (ValueError, AttributeError):
            continue
    if not slots:
        slots = [(start, 0)]
    day = due.date()
    while True:
        candidates = [datetime.combine(day, datetime.min.time()).replace(hour=h, minute=m)
                      for h, m in sorted(slots)]
        candidates = [candidate for candidate in candidates if candidate >= due]
        if candidates:
            chosen = candidates[0]
            break
        day += timedelta(days=1)
    jitter = max(0, int(config.get("fanart_schedule_jitter_minutes", 0)))
    if jitter:
        chosen += timedelta(minutes=random.randint(0, jitter))
    return chosen.timestamp()

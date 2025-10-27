import json, time
from pathlib import Path
from libs.utils.clock import get_clock
clock = get_clock()

def emit_event(event: dict, path: str = "artifacts/run_events.jsonl"):
    rec = {"ts": int(clock.time()), **event}
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")

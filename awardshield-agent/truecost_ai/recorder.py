"""recorder.py - a time-coded record of one agent run, for the UI's run replay.

    rec = Recorder("truecost", rfq_id)
    rec.event(adk_event)      # inside the runner's `async for e in runner.run_async(...)`
    rec.save(extra={...})     # -> <output_dir>/<rfq_id>/runs/truecost.json

Each entry: t (seconds since start), agent, kind (call / result / done), name, detail (short), tokens.
Only what the replay needs - no document bytes, no full prompts. Used by TrueCost ('truecost',
'truecost_answers') and RedSeal ('redseal').
"""

import json
import time
from datetime import datetime, timezone

from .settings import OUTPUT_DIR

RESULT_KEYS = ("status", "series_key", "url", "summary", "note", "proxy")


def _short(x, n: int = 220) -> str:
    s = x if isinstance(x, str) else json.dumps(x, ensure_ascii=False, default=str)
    return s if len(s) <= n else s[:n] + "..."


class Recorder:
    def __init__(self, name: str, rfq_id: str):
        self.name, self.rfq_id, self.t0 = name, rfq_id, time.time()
        self.started = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self.events: list[dict] = []

    def _add(self, agent: str, kind: str, name: str = "", detail: str = "", tokens: int | None = None) -> None:
        self.events.append({"t": round(time.time() - self.t0, 1), "agent": agent, "kind": kind, "name": name,
                            "detail": detail, **({"tokens": tokens} if tokens else {})})

    def event(self, e) -> None:
        tokens = getattr(getattr(e, "usage_metadata", None), "prompt_token_count", None)
        parts = (e.content.parts if e.content else None) or []
        for p in parts:
            if p.function_call:
                self._add(e.author, "call", p.function_call.name, _short(dict(p.function_call.args or {})), tokens)
            elif p.function_response:
                r = p.function_response.response or {}
                picked = {k: r[k] for k in RESULT_KEYS if r.get(k)}
                self._add(e.author, "result", p.function_response.name, _short(picked or r))
        if e.is_final_response() and parts:
            text = "".join(p.text or "" for p in parts if not p.thought)
            self._add(e.author, "done", detail=_short(text.strip(), 260), tokens=tokens)

    def save(self, extra: dict | None = None) -> None:
        out = OUTPUT_DIR / self.rfq_id / "runs"
        out.mkdir(parents=True, exist_ok=True)
        (out / f"{self.name}.json").write_text(json.dumps({
            "run": self.name, "rfq_id": self.rfq_id, "started_at": self.started,
            "duration_s": round(time.time() - self.t0, 1), "events": self.events, **(extra or {}),
        }, indent=1, ensure_ascii=False))

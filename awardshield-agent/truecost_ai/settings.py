"""settings.py - every switchable setting, read once from config/truecost.json.

Precedence: environment variable > config/truecost.json > the default below. The JSON file is the
place to switch things; an env var is for a one-off run. Another file: TRUECOST_SETTINGS=<path>.

    case              TRUECOST_CASE              manifest rfq_id (or path) run by default
    model             TRUECOST_MODEL             Gemini model of every step ...
    models.<step>     TRUECOST_MODEL_<STEP>      ... unless this step has its own (volume, commercial,
                                                 escalation, index_resolver, cost_model, orchestrator,
                                                 web_search, transcribe)
    temperature       TRUECOST_TEMPERATURE
    search_tool       AWARDSHIELD_SEARCH_TOOL    google_search | enterprise_web_search
    tool_timeout_s    TOOL_TIMEOUT_S
    search_timeout_s  AWARDSHIELD_SEARCH_TIMEOUT_S
    retry.attempts    TRUECOST_RETRY_ATTEMPTS    429 / 5xx retries per model call
    output_dir        TRUECOST_OUTPUT_DIR        relative to the workspace root
    state_dir         TRUECOST_STATE_DIR         buyer answers (<state_dir>/<rfq_id>/answers.json)
    max_question_rounds  TRUECOST_MAX_QUESTION_ROUNDS  runner: ask / re-link rounds after the full run
    max_parallel_bidders TRUECOST_MAX_PARALLEL_BIDDERS bidder branches running at once (more run in waves)
    vertex.use        TRUECOST_VERTEX            auto (Vertex when GOOGLE_CLOUD_PROJECT is set) | true | false
"""

import json
import os
from pathlib import Path

from google.genai import types

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "project"
KNOWN_SOURCES_PATH = ROOT / "config" / "known_sources.json"
BUYER_POLICY = ROOT / "config" / "buyer_policy.json"

try:  # before anything reads os.environ (module constants below, sub-agents at import)
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

SETTINGS_PATH = Path(os.getenv("TRUECOST_SETTINGS", ROOT / "config" / "truecost.json"))
_FILE = json.loads(SETTINGS_PATH.read_text()) if SETTINGS_PATH.exists() else {}


def setting(path: str, env: str = "", default=None):
    """'retry.attempts' -> env var if set, else the JSON value, else default (cast to its type)."""
    value = _FILE
    for part in path.split("."):
        value = value.get(part) if isinstance(value, dict) else None
    if env and os.getenv(env) not in (None, ""):
        value = os.environ[env]
    if value in (None, ""):
        return default
    if isinstance(default, bool) and isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes")
    if isinstance(default, (int, float)) and not isinstance(default, bool):
        return type(default)(value)
    return value


CASE = setting("case", "TRUECOST_CASE", "IN-CRUT-EBUS")
MODEL = setting("model", "TRUECOST_MODEL", "gemini-3.5-flash-lite")
TEMPERATURE = setting("temperature", "TRUECOST_TEMPERATURE", 0.0)
SEARCH_TOOL_NAME = setting("search_tool", "AWARDSHIELD_SEARCH_TOOL", "google_search")
TOOL_TIMEOUT_S = setting("tool_timeout_s", "TOOL_TIMEOUT_S", 60)
SEARCH_TIMEOUT_S = setting("search_timeout_s", "AWARDSHIELD_SEARCH_TIMEOUT_S", TOOL_TIMEOUT_S)
OUTPUT_DIR = ROOT / setting("output_dir", "TRUECOST_OUTPUT_DIR", "output")  # an absolute path wins
STATE_DIR = ROOT / setting("state_dir", "TRUECOST_STATE_DIR", "data/state")  # buyer answers, kept across runs
MAX_QUESTION_ROUNDS = setting("max_question_rounds", "TRUECOST_MAX_QUESTION_ROUNDS", 3)
MAX_PARALLEL_BIDDERS = max(1, setting("max_parallel_bidders", "TRUECOST_MAX_PARALLEL_BIDDERS", 5))


def model_for(step: str) -> str:
    """The model of one step: models.<step> / TRUECOST_MODEL_<STEP>, else MODEL."""
    return setting(f"models.{step}", f"TRUECOST_MODEL_{step.upper()}", MODEL)


SEARCH_MODEL = model_for("web_search")

# 429 / 5xx (quota, "high demand") are retried with backoff instead of failing the whole run
RETRY = types.HttpRetryOptions(
    attempts=setting("retry.attempts", "TRUECOST_RETRY_ATTEMPTS", 6),
    initial_delay=setting("retry.initial_delay_s", default=2.0),
    max_delay=setting("retry.max_delay_s", default=60.0),
    http_status_codes=setting("retry.status_codes", default=[408, 429, 500, 502, 503, 504]),
)


def apply_vertex_env() -> None:
    """vertex.use: 'auto' = Vertex AI when GOOGLE_CLOUD_PROJECT is set, else the Gemini API key in
    GOOGLE_API_KEY; 'true' / 'false' force it."""
    use = str(setting("vertex.use", "TRUECOST_VERTEX", "auto")).lower()
    if use == "auto":
        use = "true" if os.getenv("GOOGLE_CLOUD_PROJECT") else "false"
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE" if use in ("1", "true", "yes") else "FALSE"
    if use in ("1", "true", "yes"):
        os.environ.setdefault("GOOGLE_CLOUD_LOCATION", setting("vertex.location", default="global"))


def http_options(timeout_s: int | None = None) -> types.HttpOptions:
    return types.HttpOptions(
        timeout=timeout_s * 1000 if timeout_s is not None else None,
        retry_options=RETRY,
    )


def generate_config(
    *,
    timeout_s: int | None = None,
    model: str | None = None,
    thinking: bool | None = None,
) -> types.GenerateContentConfig:
    config: dict[str, object] = {"temperature": TEMPERATURE}
    config["http_options"] = http_options(timeout_s)
    if thinking is False:
        if (model or MODEL).lower().startswith("gemini-3"):
            config["thinking_config"] = types.ThinkingConfig(thinking_level="minimal")
        else:
            config["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
    return types.GenerateContentConfig(**config)

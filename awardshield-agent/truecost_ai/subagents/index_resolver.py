"""index_resolver.py - the index sub-agent: each escalation index -> an OFFICIAL published series.

One per bidder (make_index_resolver), after escalation_<key>. The model decides WHICH official
source; the tools below do everything with numbers (download, transcribe, validate, freeze) via
fetchers.py.

    reuse_saved_series      a series another bidder of this tender already saved
    known_source            an official page known to publish the series (config/known_sources.json)
    read_series_from_url    read + validate + freeze one official URL (printed in the bid, or found)
    web_search_<key>        sub-agent (AgentTool) that searches for official candidate URLs
    flag_for_user           nothing official found -> the buyer is asked, never a guess

Frozen series: <output>/<rfq_id>/frozen_indices/<series_key>.json (shared by all bidders).
include_contents='none': the input is state['indices_<key>'] (written from escalation_<key>); the
final answer (IndexResolutionRecord) goes to state['index_resolutions_<key>'].
"""

import asyncio
import json
import re

from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools import ToolContext

from .. import fetchers, prompts
from ..checkpoint import checkpointed
from ..schemas import IndexResolutionRecord
from ..settings import (
    KNOWN_SOURCES_PATH,
    OUTPUT_DIR,
    TOOL_TIMEOUT_S,
    generate_config,
    model_for,
)
from .web_search import SEARCH_ENABLED, make_web_search


def _frozen_dir(tool_context: ToolContext):
    return OUTPUT_DIR / tool_context.state["rfq_id"] / "frozen_indices"


def _safe_key(key: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", key.lower()).strip("_") or "series"


def _summary(annual: dict) -> str:
    years = sorted(annual, key=int)
    return f"{years[0]}-{years[-1]} ({len(years)} years), last {annual[years[-1]]}"


#
# -----------------------------------------------------------------
# tools
#
# -----------------------------------------------------------------
#


def reuse_saved_series(
    symbol: str, series_key: str, tool_context: ToolContext
) -> dict:
    """Reuse a series already saved for THIS tender (e.g. another
    bidder used the same index).
    Call this FIRST for each symbol. Returns status 'ok' with a
    summary, or 'miss'.
    """
    path = _frozen_dir(tool_context) / f"{_safe_key(series_key)}.json"
    if not path.exists():
        return {"status": "miss"}
    saved = json.loads(path.read_text())
    return {
        "status": "ok",
        "series_key": saved["series_key"],
        "url": saved["url"],
        "summary": _summary(saved["annual_values"]),
    }


def known_source(symbol: str, name: str, tool_context: ToolContext) -> dict:
    """An official page KNOWN to publish this series (for the
    tender's country), if any. Returns status 'reused' + series_key when the series is already saved;
    otherwise url, series_key (use it instead of your own),
    meaning and - when the exact statistic is not published as a
    series - a proxy note for an official
    stand-in. Read the url with read_series_from_url(...,
    step='known_source', proxy=<proxy>).
    """
    path = KNOWN_SOURCES_PATH
    hints = (
        json.loads(path.read_text()).get(
            tool_context.state.get("country", ""), []
        )
        if path.exists()
        else []
    )
    text = f"{symbol} {name}".lower()
    for h in hints:
        if any(
            re.search(rf"(?<![a-z]){re.escape(m)}(?![a-z])", text)
            for m in h["match"]
        ):
            key = h.get("series_key", "")
            saved = _frozen_dir(tool_context) / f"{key}.json" if key else None
            if saved and saved.exists():  # another bidder already saved it: reuse
                return {
                    "status": "reused",
                    "series_key": key,
                    "proxy": h.get("proxy", ""),
                    "summary": _summary(json.loads(saved.read_text())["annual_values"]),
                }
            return {
                "status": "ok",
                "series_key": key,
                "url": h["url"],
                "meaning": h["meaning"],
                "proxy": h.get("proxy", ""),
            }
    return {"status": "miss"}


async def read_series_from_url(
    symbol: str,
    series_key: str,
    url: str,
    meaning: str,
    step: str,
    tool_context: ToolContext,
    proxy: str = "",
) -> dict:
    """Read one OFFICIAL URL: the tool checks the domain is an
    official publisher, downloads the file,
    transcribes the series described by `meaning`, validates it
    and saves it as `series_key`.
    step: 'known_source', 'printed_url' (URL printed in the
    documents) or 'web' (search / own knowledge).
    proxy: the proxy note returned by known_source, when an
    official stand-in is read ('' otherwise).
    Returns status 'ok' with a summary, or 'fail' with the reason
    (do not retry a refusal) and, for a
    page, data_links: [link text, url] of the official data files
    it links to - read the matching one.
    """
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(
                fetchers.read_official_series, url, meaning
            ),
            TOOL_TIMEOUT_S,
        )
    except asyncio.TimeoutError:
        return {
            "status": "fail",
            "note": f"timeout after {int(TOOL_TIMEOUT_S)}s - try the next candidate",
        }
    except Exception as e:
        # network / parse error -> next candidate
        return {
            "status": "fail",
            "note": f"{type(e).__name__}: {str(e)[:200]}",
        }

    if result["status"] != "ok":
        return result

    key = _safe_key(series_key)
    result["provenance"]["step"] = step
    if proxy:
        result["provenance"]["proxy"] = proxy

    fetchers.freeze(_frozen_dir(tool_context), key, symbol, result)
    return {
        "status": "ok",
        "series_key": key,
        "url": url,
        "label": result["label"],
        "proxy": proxy,
        "summary": _summary(
            {str(y): v for y, v in result["annual"].items()}
        ),
        "partial_years": result["provenance"].get("partial_years", {}),
    }


def flag_for_user(symbol: str, reason: str, tool_context: ToolContext) -> dict:
    """LAST step, only after the printed URL and web steps were tried. `reason` says what each step
    returned. The buyer is asked for an official source; nothing is guessed.
    """
    agent = tool_context.agent_name
    flags = tool_context.state.get("index_flags") or []
    tool_context.state["index_flags"] = [
        f for f in flags if (f["symbol"], f.get("agent")) != (symbol, agent)
    ] + [{"symbol": symbol, "reason": reason, "agent": agent}]
    return {"status": "needs_user", "symbol": symbol}


#
# -----------------------------------------------------------------
# input: the indices of this bidder, as text for the prompt
# -----------------------------------------------------------------
#


def _tool_failed(tool, args: dict, tool_context: ToolContext, error: Exception) -> dict:
    """on_tool_error_callback: a tool that raises (e.g. web search out of quota) becomes a 'fail'
    result the model can act on, instead of an exception that stops every bidder."""
    return {"status": "fail", "note": f"{tool.name} failed - {type(error).__name__}: {str(error)[:200]}"}


def _indices_to_resolve(key: str):
    """before_agent_callback: put this bidder's indices into state['indices_<key>'].

    An agent callback, not a model callback: ADK fills the instruction's {indices_<key>} before
    before_model_callback runs, so the value must exist when the agent starts.
    """

    def callback(callback_context: CallbackContext) -> None:
        esc = callback_context.state.get(f"escalation_{key}") or {}
        lines = [
            f"- {i['symbol']}: {i.get('name', '')} | publisher: {i.get('publisher', '')} | kind: "
            f"{i.get('kind', '')} | country: {i.get('country', '')} | region: {i.get('region', '')} | "
            f"printed URL: {i.get('printed_url', '')}"
            for i in esc.get("indices", [])
        ]
        callback_context.state[f"indices_{key}"] = "\n".join(lines) or "(none)"

    return callback


NO_SEARCH_STEP = (
    "3. WEB: web search is switched off in this run. Propose an official data URL from your own "
    "knowledge (the publisher's data / time-series page) and read it with "
    "read_series_from_url(symbol, series_key, url, meaning, 'web')."
)


def _instruction(key: str) -> str:
    text = prompts.INDEX_RESOLVER.replace("{indices_to_resolve}", f"{{indices_{key}}}")
    if not SEARCH_ENABLED:  # step 3 without the search tool
        start = text.index("3. WEB:")
        text = text[:start] + NO_SEARCH_STEP + text[text.index("\n", start):]
    return text


def make_index_resolver(supplier: str, key: str) -> LlmAgent:
    return checkpointed(LlmAgent(
        name=f"index_resolver_{key}",
        model=model_for("index_resolver"),
        description=f"Resolves each escalation index of {supplier} to an official published series.",
        instruction=_instruction(key),
        tools=[
            reuse_saved_series,
            known_source,
            read_series_from_url,
            *([make_web_search(key)] if SEARCH_ENABLED else []),
            flag_for_user,
        ],
        output_schema=IndexResolutionRecord,
        output_key=f"index_resolutions_{key}",
        include_contents="none",
        before_agent_callback=_indices_to_resolve(key),
        on_tool_error_callback=_tool_failed,
        generate_content_config=generate_config(),
        disallow_transfer_to_parent=True,
        disallow_transfer_to_peers=True,
    ), inputs=[f"indices_{key}", "country"])

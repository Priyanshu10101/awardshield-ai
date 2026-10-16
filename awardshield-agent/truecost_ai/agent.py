"""agent.py - the TrueCost agent tree: every extraction step is a SUB-AGENT, one session per tender.

    root_agent = SequentialAgent "truecost"
    ├ volume_extractor
    │   LlmAgent    -> state['volume']
    ├ ParallelAgent "bidders" (every bidder at the same time)
    │   ├ SequentialAgent "bidder_<key>" (one per bidder, built from the manifest)
    │   │   ├ commercial_<key>
    │   │   │   LlmAgent    -> state['commercial_<key>']
    │   │   ├ escalation_<key>
    │   │   │   LlmAgent    -> state['escalation_<key>']
    │   │   ├ index_resolver_<key>
    │   │   │   LlmAgent    -> state['index_resolutions_<key>']
    │   │   │               (tools fetch official series; web_search_<key> is a search agent used as a tool)
    │   │   ├ cost_model_<key>
    │   │   │   LlmAgent    -> state['cost_model_<key>']
    │   │   └ finalizer_<key>
    │   │       BaseAgent   link checks, files -> state['result_<key>']
    │   └ ...
    └ orchestrator
        LlmAgent    merges every result_<key> -> state['report']

The bidder sub-agents are built per tender because an ADK agent has exactly ONE parent and each bidder needs its own state keys (suffix <key>). They all share one session and one user message holding every document; each sub-agent sees only the tender + its own bidder's documents (only_documents).

build_root(case) builds the tree for one case; `adk web` finds root_agent (built from 'case' in config/truecost.json).
run(case) runs it once: ONE session (state rfq_id, country) and ONE user message = intro + every document.
    python -m truecost_ai.agent [RFQ_ID]    one pass, prints the report
    python -m truecost_ai.runner [RFQ_ID]   the full CLI: run, ask the buyer, re-link with the answers
"""

import asyncio
import re
import sys

from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.runners import InMemoryRunner
from google.genai import types

from . import prompts
from .doc_reader import Case, pack
from .finalizer import make_finalizer
from .schemas import TenderReport
from .settings import CASE, apply_vertex_env, generate_config, model_for
from .subagents.commercial import make_commercial
from .subagents.cost_model import make_cost_model
from .subagents.escalation import make_escalation
from .subagents.index_resolver import make_index_resolver
from .subagents.volume import volume_extractor

apply_vertex_env()  # Vertex project / location for every model call


def bidder_key(supplier: str) -> str:
    """'GreenMetro' -> 'greenmetro'; a valid identifier for agent names and state keys."""
    return re.sub(r"[^a-z0-9]+", "_", supplier.lower()).strip("_")


def make_bidder(supplier: str) -> SequentialAgent:
    key = bidder_key(supplier)
    return SequentialAgent(
        name=f"bidder_{key}",
        description=f"{supplier}: commercial terms -> escalation formulae -> official index series -> cost model -> link checks and files.",
        sub_agents=[
            make_commercial(supplier, key),
            make_escalation(supplier, key),
            make_index_resolver(supplier, key),
            make_cost_model(supplier, key),
            make_finalizer(supplier, key),
        ],
    )


def make_orchestrator(case: Case) -> LlmAgent:
    keys = [bidder_key(s) for s in case.supplier_names]

    def collect(callback_context: CallbackContext) -> None:
        """before_agent_callback: put every bidder's result into state ['bidder_results'] for the prompt."""
        st = callback_context.state
        st["title"] = case.title
        st["bidder_results"] = [
            st.get(f"result_{k}")
            or {
                "supplier": s,
                "status": "failed",
                "problems": ["the bidder's sub-agents did not finish"],
            }
            for s, k in zip(case.supplier_names, keys)
        ]

    return LlmAgent(
        name="orchestrator",
        model=model_for("orchestrator"),
        description="Merges every bidder's result into one report and the questions the buyer must answer.",
        instruction=prompts.ORCHESTRATOR,
        output_schema=TenderReport,
        output_key="report",
        include_contents="none",
        before_agent_callback=collect,
        generate_content_config=generate_config(),
        disallow_transfer_to_parent=True,
        disallow_transfer_to_peers=True,
    )


def build_root(case: Case) -> SequentialAgent:
    return SequentialAgent(
        name="truecost",
        description=f"TrueCost for {case.rfq_id}: tender volume, every bidder in parallel, merged report.",
        sub_agents=[
            volume_extractor.clone(),
            ParallelAgent(
                name="bidders",
                description="Every bidder's pipeline at the same time.",
                sub_agents=[make_bidder(s) for s in case.supplier_names],
            ),
            make_orchestrator(case),
        ],
    )


def intro(case: Case) -> str:
    return (
        f"Tender {case.rfq_id}: {case.title} ({case.country}, {case.currency}). "
        f"Bidders: {', '.join(case.supplier_names)}. "
        "Every document follows, each after its '--- DOCUMENT (...)' header."
    )


async def run(case: Case) -> dict:
    """One session for the whole tender; returns the final state (report under 'report')."""
    runner = InMemoryRunner(agent=build_root(case), app_name="truecost")
    session = await runner.session_service.create_session(
        app_name="truecost",
        user_id="buyer",
        state={"rfq_id": case.rfq_id, "country": case.country},
    )
    message = types.Content(role="user", parts=[types.Part(text=intro(case)), *pack(case.documents)])
    async for event in runner.run_async(
        user_id="buyer", session_id=session.id, new_message=message
    ):
        if event.content and event.content.parts and event.content.parts[0].text and not event.partial:
            print(f"[{event.author}] {event.content.parts[0].text[:300]}")
    session = await runner.session_service.get_session(
        app_name="truecost", user_id="buyer", session_id=session.id
    )
    return session.state


root_agent = build_root(Case.load(CASE))

if __name__ == "__main__":
    import json

    case = Case.load(sys.argv[1] if len(sys.argv) > 1 else CASE)
    state = asyncio.run(run(case))
    print(json.dumps(state.get("report"), indent=1, ensure_ascii=False))

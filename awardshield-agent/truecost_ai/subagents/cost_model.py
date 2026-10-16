"""cost_model.py - the cost-model sub-agent: ONE bidder's records -> CostModelDraft.

One per bidder (make_cost_model), after commercial / escalation / index_resolver of that bidder.
It reads NO documents: its prompt receives the records from state ({volume}, {commercial_<key>},
{escalation_<key>}, {index_resolutions_<key>}, {policy}, {answers?}) and the recipe the engine
evaluates. The validated draft is stored in state["cost_model_<key>"].

include_contents='none': the PDFs are earlier in the session; this agent works only from the records.
"""

import json

from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext

from .. import prompts
from ..checkpoint import checkpointed
from ..schemas import CostModelDraft
from ..settings import BUYER_POLICY, generate_config, model_for


def _load_policy(callback_context: CallbackContext) -> None:
    """before_agent_callback: put the company policy into state['policy'] (once per session)."""
    if "policy" not in callback_context.state:
        policy = json.loads(BUYER_POLICY.read_text()) if BUYER_POLICY.exists() else {}
        callback_context.state["policy"] = {k: v for k, v in policy.items()}


def make_cost_model(supplier: str, key: str) -> LlmAgent:
    instruction = prompts.COST_MODEL.replace("{supplier}", supplier)
    for name in ("commercial", "escalation", "index_resolutions"):
        instruction = instruction.replace(f"{{{name}}}", f"{{{name}_{key}}}")
    return checkpointed(LlmAgent(
        name=f"cost_model_{key}",
        model=model_for("cost_model"),
        description=f"Links {supplier}'s extraction records into its cost model (parameters, "
        "escalators, lines), every value sourced.",
        instruction=instruction,
        output_schema=CostModelDraft,
        output_key=f"cost_model_{key}",
        include_contents="none",
        before_agent_callback=_load_policy,
        generate_content_config=generate_config(),
        disallow_transfer_to_parent=True,
        disallow_transfer_to_peers=True,
    ), inputs=["volume", f"commercial_{key}", f"escalation_{key}", f"index_resolutions_{key}", "policy", "answers"])

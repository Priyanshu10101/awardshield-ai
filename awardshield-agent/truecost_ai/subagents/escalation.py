"""escalation.py - the escalation sub-agent: reads ONE bidder's documents -> EscalationRecord.

One per bidder (make_escalation), AFTER commercial_<key>: its prompt reads {commercial_<key>?}
from state so applies_to can use that bidder's term_ids. only_documents hides the other bidders'
bids. The validated answer is stored in state["escalation_<key>"].
"""

from google.adk.agents import LlmAgent

from .. import prompts
from ..checkpoint import checkpointed
from ..doc_reader import only_documents
from ..schemas import EscalationRecord
from ..settings import generate_config, model_for


def make_escalation(supplier: str, key: str) -> LlmAgent:
    instruction = prompts.ESCALATION.replace("{supplier}", supplier).replace(
        "{commercial?}", f"{{commercial_{key}?}}"
    )
    return checkpointed(LlmAgent(
        name=f"escalation_{key}",
        model=model_for("escalation"),
        description=f"Reads {supplier}'s documents and returns its price-escalation formulae and their indices.",
        instruction=instruction,
        output_schema=EscalationRecord,
        output_key=f"escalation_{key}",
        before_model_callback=only_documents(True, supplier),
        generate_content_config=generate_config(),
        disallow_transfer_to_parent=True,
        disallow_transfer_to_peers=True,
    ), inputs=[f"commercial_{key}"])

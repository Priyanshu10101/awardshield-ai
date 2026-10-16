"""commercial.py - the commercial sub-agent: reads ONE bidder's documents -> CommercialRecord.

One per bidder (make_commercial), first in the bidder's sequence. Every document is in the
session's user message; only_documents hides the other bidders' bids. The bidder's name is
written into the prompt; the validated answer is stored in state["commercial_<key>"].
"""

from google.adk.agents import LlmAgent

from .. import prompts
from ..checkpoint import checkpointed
from ..doc_reader import only_documents
from ..schemas import CommercialRecord
from ..settings import generate_config, model_for


def make_commercial(supplier: str, key: str) -> LlmAgent:
    return checkpointed(LlmAgent(
        name=f"commercial_{key}",
        model=model_for("commercial"),
        description=f"Reads {supplier}'s documents and returns every priced / commercial term as printed.",
        instruction=prompts.COMMERCIAL.replace("{supplier}", supplier),
        output_schema=CommercialRecord,
        output_key=f"commercial_{key}",
        before_model_callback=only_documents(True, supplier),
        generate_content_config=generate_config(),
        disallow_transfer_to_parent=True,
        disallow_transfer_to_peers=True,
    ))

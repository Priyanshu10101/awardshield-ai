"""volume.py - the volume sub-agent: reads the TENDER and returns a VolumeRecord.

Runs once per tender, first. Every document is in the user message (doc_reader.pack);
only_documents(tender=True) hides the bids. The agent answers with JSON matching VolumeRecord,
which ADK validates and stores in state["volume"]. No tools: output_schema alone forces the shape.
"""

from google.adk.agents import LlmAgent

from .. import prompts
from ..checkpoint import checkpointed
from ..doc_reader import only_documents
from ..schemas import VolumeRecord
from ..settings import generate_config, model_for

volume_extractor = checkpointed(LlmAgent(
    name="volume_extractor",
    model=model_for("volume"),
    description="Reads the tender and returns the volume to be priced and the tender's contract facts.",
    instruction=prompts.VOLUME,
    output_schema=VolumeRecord,
    output_key="volume",
    before_model_callback=only_documents(tender=True),
    generate_content_config=generate_config(),
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
))

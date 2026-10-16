"""checkpoint.py - resume a run where it stopped: every model step's answer is saved the moment it
finishes, and a re-run restores it instead of calling the model again.

checkpointed(agent, inputs) adds two callbacks to an LlmAgent:
  before_agent_callback  a saved answer exists -> skip the agent; the callback's reply IS the saved
                         answer (ADK writes an agent's reply to output_key, a callback's reply too)
  after_agent_callback   the agent produced state[output_key] -> save it

File: <checkpoint_dir>/<output_key>.<hash>.json. The hash covers what the answer depends on: the
agent's instruction, its model and the state values it reads (`inputs`, e.g. commercial_<key>).
Change a prompt, a model, an upstream record or a buyer answer and the step runs again; the
documents are covered by checkpoint_dir itself (runner: <state_dir>/<rfq_id>/checkpoints/<docs hash>).

Only active when state['checkpoint_dir'] is set (the runner sets it); `runner --fresh` clears it.
"""

import hashlib
import json
from pathlib import Path

from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.genai import types

RESTORED = "checkpoint_restored"  # state key: name of the last agent restored from a checkpoint


def _path(agent: LlmAgent, inputs: list[str], state) -> Path | None:
    folder = state.get("checkpoint_dir")
    if not folder:
        return None
    basis = [agent.instruction, str(agent.model), [state.get(k) for k in inputs]]
    digest = hashlib.sha256(json.dumps(basis, sort_keys=True, default=str).encode()).hexdigest()[:12]
    return Path(folder) / f"{agent.output_key}.{digest}.json"


def _as_list(callback) -> list:
    return [] if callback is None else list(callback) if isinstance(callback, list) else [callback]


def checkpointed(agent: LlmAgent, inputs: list[str] = ()) -> LlmAgent:
    """Make `agent` resumable; `inputs` = the state keys its prompt reads (besides the documents)."""
    inputs = list(inputs)

    def restore(callback_context: CallbackContext) -> types.Content | None:
        path = _path(agent, inputs, callback_context.state)
        if path is None or not path.exists():
            return None
        saved = json.loads(path.read_text())
        callback_context.state[RESTORED] = agent.name  # the runner shows the step as restored
        text = saved if isinstance(saved, str) else json.dumps(saved, ensure_ascii=False)
        return types.Content(role="model", parts=[types.Part(text=text)])

    def save(callback_context: CallbackContext) -> None:
        path = _path(agent, inputs, callback_context.state)
        value = callback_context.state.get(agent.output_key)
        if path is None or value is None:
            return None
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(value, indent=1, ensure_ascii=False))
        tmp.replace(path)  # never a half-written checkpoint
        return None

    # after the agent's own before-callbacks: they only fill state (policy, indices) the hash may read
    agent.before_agent_callback = [*_as_list(agent.before_agent_callback), restore]
    agent.after_agent_callback = [*_as_list(agent.after_agent_callback), save]
    return agent

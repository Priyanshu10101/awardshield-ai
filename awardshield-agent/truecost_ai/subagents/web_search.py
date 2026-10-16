"""web_search.py - the web-search sub-agent: finds the OFFICIAL page that publishes one statistic.

Why a separate agent: Gemini's built-in search tool cannot be combined with ordinary Python tools
in one agent, so it runs alone and the index resolver calls it as a tool (AgentTool). Its input is
the request text the resolver writes (symbol, name, publisher, country); its answer is JSON with
candidate URLs, which the resolver passes to fetchers.read_official_series - that function
re-checks the domain is official before anything is read.

One per index resolver (make_web_search): an ADK agent has exactly one parent.

Search tool: 'search_tool' in config/truecost.json - google_search (Gemini API key),
enterprise_web_search (Vertex Web Grounding for Enterprise, where consumer search is blocked) or
none (no search quota: the resolver goes straight to official URLs from its own knowledge).
"""

from google.adk import tools as adk_tools
from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool

from .. import prompts
from ..settings import SEARCH_MODEL, SEARCH_TIMEOUT_S, SEARCH_TOOL_NAME, generate_config

SEARCH_ENABLED = SEARCH_TOOL_NAME.strip().lower() not in ("", "none", "off")
SEARCH_TOOL = getattr(adk_tools, SEARCH_TOOL_NAME) if SEARCH_ENABLED else None


def make_web_search(key: str) -> AgentTool:
    agent = LlmAgent(
        name=f"web_search_{key}",
        model=SEARCH_MODEL,
        description=(
            "Web-searches for the OFFICIAL page that publishes one economic index. Pass a request "
            "naming the index symbol, full printed name, publisher, country and region. Returns "
            "JSON candidates (url, publisher, why); read the best one with read_series_from_url."
        ),
        instruction=prompts.WEB_SEARCH,
        tools=[SEARCH_TOOL],
        generate_content_config=generate_config(
            timeout_s=SEARCH_TIMEOUT_S, model=SEARCH_MODEL, thinking=False
        ),
    )
    return AgentTool(agent=agent)

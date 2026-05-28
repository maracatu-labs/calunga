import logging

from langgraph.prebuilt import create_react_agent

from app.agent.llm import create_llm
from app.agent.prompts import build_system_prompt
from app.agent.tools import ALL_TOOLS

logger = logging.getLogger(__name__)

AGENT_RECURSION_LIMIT = 8

def create_agent(model: str | None = None):
    llm = create_llm(model=model)
    return create_react_agent(
        llm,
        tools=ALL_TOOLS,
        prompt=build_system_prompt(),
    )

def get_agent_config() -> dict:
    """LangGraph config applied to every invocation.

    recursion_limit caps tool-call → LLM → tool-call iterations. LangGraph's
    default is 25; we lower it to 8 because real queries resolve in 1-4
    iterations and long loops just burn Gemini tokens without adding value.
    """
    return {"recursion_limit": AGENT_RECURSION_LIMIT}

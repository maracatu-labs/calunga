import logging

from langgraph.prebuilt import create_react_agent

from app.agent.llm import create_llm
from app.agent.prompts import build_system_prompt
from app.agent.tools import ALL_TOOLS

logger = logging.getLogger(__name__)

def create_agent(model: str | None = None):
    llm = create_llm(model=model)
    return create_react_agent(
        llm,
        tools=ALL_TOOLS,
        prompt=build_system_prompt(),
    )

def get_agent_config() -> dict:
    """Retorna config dict para o agente."""
    return {}

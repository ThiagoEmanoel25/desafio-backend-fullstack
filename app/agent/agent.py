"""The chat agent: turns a natural-language message into a task via a tool."""

from pydantic_ai import Agent

from app.agent.deps import AgentDeps
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import create_task_tool
from app.config import settings

agent = Agent(
    settings.LLM_MODEL,
    deps_type=AgentDeps,
    instructions=SYSTEM_PROMPT,
    tools=[create_task_tool],
)

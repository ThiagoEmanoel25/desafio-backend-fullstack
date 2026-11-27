"""The chat agent: turns a natural-language message into a task via a tool."""

from datetime import datetime
from zoneinfo import ZoneInfo

from pydantic_ai import Agent, Tool

from app.agent.deps import AgentDeps
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import create_task_tool, list_tasks, search_task_memory
from app.config import settings

agent = Agent(
    settings.LLM_MODEL,
    deps_type=AgentDeps,
    instructions=SYSTEM_PROMPT,
    # All tools share one AsyncSession, which cannot run two queries at once.
    tools=[
        Tool(create_task_tool, sequential=True),
        Tool(list_tasks, sequential=True),
        Tool(search_task_memory, sequential=True),
    ],
)


@agent.instructions
def calendar_context() -> str:
    today = datetime.now(ZoneInfo("America/Bahia")).date()
    return f"Today's date is {today.isoformat()} in America/Bahia."

"""ORM models.

Import every model here so that `Base.metadata` knows about all tables
(Alembic autogenerate relies on this).
"""

from app.models.ai_usage import AIUsage
from app.models.base import Base
from app.models.task import Task
from app.models.task_search_index import TaskSearchIndex
from app.models.user import User

__all__ = ["AIUsage", "Base", "Task", "TaskSearchIndex", "User"]

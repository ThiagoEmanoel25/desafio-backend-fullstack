"""ORM models.

Import every model here so that `Base.metadata` knows about all tables
(Alembic autogenerate relies on this).
"""

from app.models.base import Base
from app.models.task import Task
from app.models.task_search_index import TaskSearchIndex
from app.models.user import User

__all__ = ["Base", "Task", "TaskSearchIndex", "User"]

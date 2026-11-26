"""Model-level guard: `updated_at` is refreshed on UPDATE and readable in async."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Task, User


async def test_updated_at_is_loaded_after_update(db_session: AsyncSession) -> None:
    user = User(email="a@example.com", full_name="A", hashed_password="x")
    db_session.add(user)
    await db_session.commit()
    task = Task(title="abc", department="ops", user_id=user.id)
    db_session.add(task)
    await db_session.commit()
    before = task.updated_at

    task.title = "changed"
    await db_session.commit()

    # No refresh() and no lazy load: eager_defaults must have fetched it.
    assert task.updated_at > before

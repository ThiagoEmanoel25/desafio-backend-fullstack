"""Create an admin explicitly: python -m seed.create_admin (interactive)."""

import asyncio
from getpass import getpass

from app.core.database import async_session_maker, engine
from app.core.security import hash_password
from app.models.user import User
from app.repositories.user_repository import get_by_email
from app.schemas.auth import RegisterRequest


async def main():
    data = RegisterRequest(
        email=input("Admin email: ").strip(),
        full_name=input("Full name: ").strip(),
        password=getpass("Password (8+ characters): "),
    )
    async with async_session_maker() as db:
        if await get_by_email(db, data.email):
            raise ValueError("Account already exists; no privilege was changed")
        db.add(
            User(
                email=data.email,
                full_name=data.full_name,
                hashed_password=hash_password(data.password),
                is_admin=True,
            )
        )
        await db.commit()
    await engine.dispose()
    print("Administrator created")


if __name__ == "__main__":
    asyncio.run(main())

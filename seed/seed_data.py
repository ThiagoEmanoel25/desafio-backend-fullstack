"""Seed the database with two users and their tasks.

Idempotent: users are matched by e-mail and tasks by `(user_id, title)`, so a
second run creates nothing new and raises nothing.

Run with `docker compose exec api python -m seed.seed_data`, or with
`python -m seed.seed_data` locally once `DATABASE_URL` points at the exposed
Postgres port. The credentials are documented in `README.md`.

Both users get several open tasks in the same department on purpose: that is
what makes the task assistant's related-task context visible, and two users
with their own tasks is what makes the per-user isolation visible.
"""

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker, engine
from app.core.security import hash_password
from app.models.task import Task
from app.models.user import User
from app.schemas.task import TaskPriority, TaskStatus
from app.services.task_retrieval import backfill_index

PASSWORD = "password123"

SEED_USERS = [
    {
        "email": "ana@example.com",
        "full_name": "Ana Souza",
        "tasks": [
            {
                "title": "Revisar relatório financeiro do trimestre",
                "description": (
                    "Conferir os números do fechamento com a contabilidade "
                    "antes da reunião de diretoria."
                ),
                "status": TaskStatus.pending,
                "priority": TaskPriority.urgent,
                "department": "Financeiro",
            },
            {
                "title": "Fechar proposta comercial da Acme",
                "description": "Ajustar desconto e prazo de pagamento com o cliente.",
                "status": TaskStatus.in_progress,
                "priority": TaskPriority.high,
                "department": "Comercial",
            },
            {
                "title": "Preparar apresentação para o cliente Acme",
                "description": "Slides com escopo, cronograma e investimento.",
                "status": TaskStatus.pending,
                "priority": TaskPriority.medium,
                "department": "Comercial",
            },
            {
                # No description on purpose: the assistant should ask questions.
                "title": "Atualizar planilha de comissões",
                "description": None,
                "status": TaskStatus.pending,
                "priority": TaskPriority.low,
                "department": "Comercial",
            },
            {
                "title": "Arquivar contratos de 2025",
                "description": "Digitalizar e guardar na pasta do jurídico.",
                "status": TaskStatus.completed,
                "priority": TaskPriority.low,
                "department": "Financeiro",
            },
        ],
    },
    {
        "email": "bruno@example.com",
        "full_name": "Bruno Lima",
        "tasks": [
            {
                "title": "Corrigir bug de login intermitente",
                "description": (
                    "Alguns usuários recebem 401 logo após entrar. "
                    "Reproduzir e corrigir."
                ),
                "status": TaskStatus.in_progress,
                "priority": TaskPriority.urgent,
                "department": "Engenharia",
            },
            {
                "title": "Escrever testes do módulo de tarefas",
                "description": "Cobrir CRUD e isolamento entre usuários.",
                "status": TaskStatus.pending,
                "priority": TaskPriority.high,
                "department": "Engenharia",
            },
            {
                # No description on purpose: the assistant should ask questions.
                "title": "Migrar pipeline de deploy",
                "description": None,
                "status": TaskStatus.pending,
                "priority": TaskPriority.medium,
                "department": "Engenharia",
            },
            {
                "title": "Responder tickets pendentes do suporte",
                "description": "Fila acumulada da última semana.",
                "status": TaskStatus.pending,
                "priority": TaskPriority.medium,
                "department": "Suporte",
            },
            {
                "title": "Documentar processo de onboarding",
                "description": "Passo a passo para novos integrantes do time.",
                "status": TaskStatus.completed,
                "priority": TaskPriority.low,
                "department": "Suporte",
            },
        ],
    },
]


async def _seed_user(db: AsyncSession, spec: dict) -> None:
    """Create the user and any of its tasks that is not there yet."""
    user = (
        await db.execute(select(User).where(User.email == spec["email"]))
    ).scalar_one_or_none()
    if user is None:
        user = User(
            email=spec["email"],
            full_name=spec["full_name"],
            hashed_password=hash_password(PASSWORD),
            is_active=True,
        )
        db.add(user)
        await db.flush()
        print(f"  user {spec['email']}: created")
    else:
        print(f"  user {spec['email']}: already there, skipped")

    existing_titles = set(
        (await db.execute(select(Task.title).where(Task.user_id == user.id))).scalars()
    )
    missing = [t for t in spec["tasks"] if t["title"] not in existing_titles]
    db.add_all(Task(**task, user_id=user.id) for task in missing)
    print(
        f"  tasks: {len(missing)} created, {len(spec['tasks']) - len(missing)} skipped"
    )


async def main() -> None:
    """Seed every user in `SEED_USERS` and commit once."""
    print("Seeding...")
    async with async_session_maker() as db:
        for spec in SEED_USERS:
            await _seed_user(db, spec)
        await db.flush()
        # Index existing and new tasks; unchanged ones are skipped by hash.
        print(f"  search index: {await backfill_index(db)} tasks checked")
        await db.commit()
    await engine.dispose()
    print("Done. The credentials are in README.md.")


if __name__ == "__main__":
    asyncio.run(main())

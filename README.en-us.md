# Technical Challenge — Junior FullStack Developer (Backend Focus · Python / AI)

> 🇧🇷 Versão em português: [README.md](README.md)

## Objective

You will build a **task manager with an AI assistant**: each user logs in, manages their own tasks through a React interface, can ask an AI agent, in natural language, to create tasks for them, and can ask the AI to **evaluate a task and build a plan to execute it**.

The focus is the **backend**. We want to evaluate your ability to build a clean, validated and well-organized API, and to integrate an AI agent into a real product flow. The frontend is simpler and is there to show you can consume your own API.

We don't expect a perfect system. We prefer **simple, readable, well-explained code** over many half-finished features. If you can't finish something, write in the README what is missing and how you would do it.

## Tech Stack

| Layer | Technologies |
|---|---|
| Language | Python 3.11+ (`async`/`await` and type hints) |
| Web Framework | FastAPI (async routes, `Depends`, automatic Swagger) |
| Validation | Pydantic v2 |
| AI | PydanticAI (agent + tool calling) |
| Database | PostgreSQL + SQLAlchemy 2.0 (async) + Alembic |
| Frontend | React + TypeScript (Vite). **Next.js is also accepted** |
| Infra | Docker and Docker Compose |
| Standards | PEP8 (ruff), code and logs in English, standardized commits |

## What is already provided

So you can focus on what matters, the repository already includes:

- ✅ **Docker Compose** with the API, PostgreSQL and the frontend (`docker compose up --build`)
- ✅ Typed **settings** with `pydantic-settings` ([app/config.py](app/config.py))
- ✅ **Async database connection** ([app/core/database.py](app/core/database.py)) and the `get_db()` dependency ([app/api/deps.py](app/api/deps.py))
- ✅ **Security helpers**: password hashing (bcrypt) and JWT creation/validation ([app/core/security.py](app/core/security.py))
- ✅ A ready **`User` model** to use as a reference ([app/models/user.py](app/models/user.py))
- ✅ **Alembic** configured and the v1 **router** already registered
- ✅ A **test HTTP client** (`async_client`) and an example test ([tests/](tests/))
- ✅ A **frontend skeleton** in React + TypeScript that already builds, with an HTTP client, pages and components ([frontend/](frontend/))

Every file you need to complete has a header comment saying **"You should implement here"** that explains what is expected.

> **Note:** this section and **Challenge Scope** below are the original brief, written for whoever was going to implement the challenge. They mention `TODO`s and "You should implement here" comments that **no longer exist** in the code: everything required has been implemented. What was actually delivered is described in [How to Run](#how-to-run), [Running the tests](#running-the-tests) and [Project Structure](#project-structure), and the questionnaire is answered in the Portuguese [README.md](README.md).

## Challenge Scope

### Part 1: Authentication and Task CRUD (required)

1. **JWT authentication**
   - `POST /v1/auth/register`: creates a user (password stored hashed).
   - `POST /v1/auth/login`: validates credentials and returns a JWT.
   - `GET /v1/auth/me`: returns the authenticated user.
   - Implement the `get_current_user()` dependency in [app/api/deps.py](app/api/deps.py).

2. **Task CRUD** (`/v1/tasks`)
   - Create, list, get by ID, partially update (`PATCH`) and delete.
   - Fields: `title`, `description`, `status` (`pending` / `in_progress` / `completed`), `priority` (`low` / `medium` / `high` / `urgent`), `department`, `created_at` and `updated_at`.
   - Validation with **Pydantic v2 schemas** and `response_model` on the routes.

3. **Per-user isolation** 🔒
   - Each task belongs to one user (`user_id`).
   - A user must **never** see, change or delete another user's tasks. Accessing another user's task must return `404`.

4. **Database**
   - A `Task` model with SQLAlchemy 2.0 (`Mapped[...]` style).
   - At least **one Alembic migration** creating the tables.

### Part 2: AI Agent with PydanticAI (required)

1. **`POST /v1/chat` endpoint** (authenticated): receives the user's message and returns the agent's answer.
2. A **PydanticAI agent** with a clear system prompt ([app/agent/](app/agent/)).
3. A **`create_task` tool**: the agent extracts the information from the message, validates it with the Pydantic `TaskCreate` schema and creates the task in the database **for the logged-in user**.

**Expected scenario:** when sending *"Cadastre uma tarefa urgente chamada 'Revisar relatório financeiro' para o departamento Comercial"* ("Register an urgent task called 'Review financial report' for the Commercial department"), a task with `priority=urgent` and `department=Comercial` must be created for the authenticated user.

4. **Error handling:** if the LLM provider fails, the API must return a controlled error (e.g. `503`), not a generic 500.

> 💡 **You don't need to pay for an LLM API.** Pick one option in `.env`:
> - `LLM_MODEL=test`: PydanticAI's fake model, no key needed. It calls your tools with dummy data, which is great for development.
> - `LLM_MODEL=ollama:llama3.2`: a free local LLM via [Ollama](https://ollama.com).
> - `LLM_MODEL=google:gemini-3.8-flash`: Gemini, which has a free tier.
> - `LLM_MODEL=openai:<model>`: OpenAI.
>
> In **automated tests**, use PydanticAI's `TestModel` (see [tests/conftest.py](tests/conftest.py)). Tests must not call a real LLM.

### Part 3: AI Task Assistant (required)

Besides creating tasks, the AI must **help the user execute them**. In this part we mainly evaluate how you work with **context**: what information the LLM receives, where it comes from and what is left out.

1. **`POST /v1/tasks/{task_id}/assist` endpoint** (authenticated): the AI evaluates the task and returns a plan.
2. **A second PydanticAI agent** ([app/agent/task_assistant.py](app/agent/task_assistant.py)), separate from the chat agent, with **structured output** (`output_type`) using the `TaskAssistance` schema ([app/schemas/assistance.py](app/schemas/assistance.py)):
   - task summary and complexity (`low` / `medium` / `high`);
   - effort estimate in hours;
   - suggested priority, with a reason (does the current priority make sense?);
   - concrete, ordered steps to execute the task;
   - risks and attention points;
   - clarifying questions when information is missing.
3. **Context building** ([app/services/task_assistant_service.py](app/services/task_assistant_service.py)):
   - the task is loaded from the database **filtered by the logged-in user** (another user's task returns `404`);
   - include **small, relevant** extra context, e.g. up to 5 other open tasks of the same user in the same department;
   - inject this context through **dynamic instructions** (`@agent.instructions` + `RunContext`), separate from the static prompt;
   - do not send unnecessary or sensitive data to the LLM (password hashes, emails, other users' data, the whole table).
4. If the task has little information (e.g. no description), the AI must **say so and ask questions** instead of inventing details.
5. **Explain in the README** what information you sent to the LLM and why.

### Part 4: React Frontend (required)

The skeleton is in [frontend/](frontend/). Complete the parts marked with `TODO` *(all six items below are implemented)*:

1. A **login page** that stores the token and shows errors.
2. The user's **task list**, with loading, empty and error states.
3. A **form** to create tasks.
4. **Actions** to change the status and delete tasks.
5. A **chat panel** with the AI agent. When the agent creates a task, the list must be refreshed.
6. An **"Ask AI for help"** button on each task, opening the [TaskAssistantPanel](frontend/src/components/TaskAssistantPanel.tsx) with the evaluation and the execution plan.

On the backend, configure **CORSMiddleware** so the frontend can call the API. *(Done: it is in [app/main.py](app/main.py), with the origins coming from `settings.cors_origins_list` — never `"*"`.)*

We do not evaluate visual design. We evaluate **API consumption, state management and component organization**. Any library is welcome (Tailwind, MUI, React Query, etc.). If you prefer **Next.js**, you may replace the `frontend/` folder, as long as the project still runs with Docker Compose.

### Part 5: Quality and standards (required)

- **Automated tests** (pytest): at least login, CRUD, isolation between users, chat and the task assistant (with `TestModel`). The files in [tests/](tests/) list the suggested scenarios.
- **Structured logs** (JSON or key=value) in [app/core/logging.py](app/core/logging.py). Log at least task creation and agent calls.
- **API documentation**: docstrings on routes and `summary`/`description` where it makes sense. Remember that Swagger is generated from them.
- A **seed** with at least 2 users and some tasks ([seed/seed_data.py](seed/seed_data.py)). Document the credentials in the README.
- **Commits** that are small and clear, following [Conventional Commits](https://www.conventionalcommits.org/) (e.g. `feat: add task CRUD endpoints`), on git-flow-style branches (`feature/...`).
- Code passing `ruff check .`.

### Nice to have (optional)

Only work on these after finishing the required scope. They are **not needed** to pass.

- An extra agent tool, e.g. `list_tasks` (*"what are my urgent tasks?"*).
- Cache the assistant's evaluation so the LLM is not called again until the task changes.
- Follow-up questions about the same task, keeping the conversation history (`message_history`).
- Filters and pagination on the task list.
- FastAPI **BackgroundTasks** to write an audit log when a task is created.
- **Redis** as a cache for the task list, invalidated on create, update or delete.
- Frontend tests (Vitest + Testing Library).
- React Query or a state management library.
- A CI pipeline (GitHub Actions) running lint and tests.

## Evaluation Criteria

| Criterion | Weight | What we look at |
|---|---|---|
| Backend: API and data | 30% | Async routes, use of `Depends`, Pydantic schemas, models, migration, layering (route → service → repository) |
| AI agents and context | 25% | Agent organization, prompt clarity, Pydantic-validated tool, structured output, context selection and building, LLM error handling |
| Security | 15% | JWT, hashed passwords, isolation between users |
| Frontend | 15% | API consumption, loading/error states, component organization |
| Quality | 15% | Tests, readability, logs, README, commit history |

## Technical Questionnaire

Answer in your own words, short and to the point. There is no single right answer: we want to understand your reasoning.

### 1. Async in FastAPI

What is the difference between declaring a route with `async def` and with `def` in FastAPI? In which situation can `async def` **hurt** performance?

**Answer:** written in Portuguese in the main README: [answer](README.md#1-async-no-fastapi).

### 2. Agent flow

Describe, step by step, what happens from the moment the user sends the chat message until the task is saved in the database. Where does Pydantic validation come in?

**Answer:** written in Portuguese in the main README: [answer](README.md#2-fluxo-do-agente).

### 3. Assistant context

What information did you send to the LLM in the task assistant, and what did you decide to leave out? How does that choice affect answer quality, cost (tokens) and user privacy?

**Answer:** written in Portuguese in the main README: [answer](README.md#3-contexto-do-assistente).

### 4. Security with AI

Why must the `user_id` used by the tool come from the request context (`ctx.deps`) and not from a parameter filled in by the LLM? What could go wrong in the second case?

**Answer:** written in Portuguese in the main README: [answer](README.md#4-segurança-com-ia).

### 5. Next steps

If you had one more week, what would you improve or add to the project, and why?

**Answer:** written in Portuguese in the main README: [answer](README.md#5-próximos-passos).

## How to Run

### Prerequisites

- Docker and Docker Compose
- (Optional) Python 3.11+ and Node.js 24 LTS (or 22.22+) to run outside Docker. The app itself runs on Node 20.19+, but the frontend tests (Vitest 5 + jsdom) need 22.22+ or 24.15+; the frontend Docker image already uses `node:24-alpine`.

### With Docker Compose (recommended)

```bash
cp .env.example .env
docker compose up --build
```

| Service | URL |
|---|---|
| API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| Frontend | http://localhost:5173 |
| PostgreSQL | `localhost:5433` (change it with `POSTGRES_HOST_PORT` if the port is in use) |
| Redis | `localhost:6379` (change it with `REDIS_HOST_PORT` if the port is in use) |

With the containers up, apply the migration and load the seed (**this is what creates the test users**):

```bash
docker compose exec api alembic upgrade head
docker compose exec api python -m seed.seed_data
```

Other useful commands:

```bash
docker compose exec api ruff check .
docker compose exec db createdb -U app desafio_test   # once, the suite needs its own database
docker compose exec -e TEST_DATABASE_URL=postgresql+asyncpg://app:app@db:5432/desafio_test api pytest -v
```

### Seed credentials

| E-mail | Password |
|---|---|
| `ana@example.com` | `password123` |
| `bruno@example.com` | `password123` |

```bash
# inside Docker
docker compose exec api python -m seed.seed_data
# locally (with the variables from the "Locally" section exported)
python -m seed.seed_data
```

Each user gets 5 tasks across different statuses, priorities and departments, with more than
one open task in the same department (that is what the assistant's related-task context uses)
and one task without a description on purpose. The seed is **idempotent**: it looks users up
by e-mail and tasks by `(user_id, title)`, so running it twice duplicates nothing.

### Locally (API outside Docker)

```bash
# 1. Start only the database and Redis (localhost:5433 and localhost:6379;
#    change them with POSTGRES_HOST_PORT / REDIS_HOST_PORT if a port is in use)
docker compose up db redis -d --wait

# 2. Create the test database (once)
docker compose exec db createdb -U app desafio_test

# 3. Python environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt

# 4. Point the URLs at the exposed port, in this shell only
#    (do not edit .env - see the note below)
export DATABASE_URL=postgresql+asyncpg://app:app@localhost:5433/desafio
export TEST_DATABASE_URL=postgresql+asyncpg://app:app@localhost:5433/desafio_test
export REDIS_URL=redis://localhost:6379/0   # the REDIS_HOST_PORT port, if you changed it
export PYDANTIC_AI_NO_BANNER=1

# 5. Migration, seed and API
alembic upgrade head
python -m seed.seed_data
uvicorn app.main:app --reload
```

**Why export instead of editing `.env`:** `.env` is the file `docker compose` hands to the
container, where the database is `db:5432`. Changing `DATABASE_URL` there breaks the
containerised API. Environment variables win over `.env` in pydantic-settings, so exporting in
your shell fixes the local case without breaking the Docker one. `REDIS_URL` follows the same rule
(`redis:6379` inside Docker, `localhost` outside); without it the API still works, but with no cache
and no chat history, logging `cache_degraded`. Keep the `export` lines in a
`.dev-env.sh` of your own (it is in `.gitignore`) and `source` it before `pytest`, `alembic`,
`uvicorn` and the seed.

### Running the tests

```bash
export TEST_DATABASE_URL=postgresql+asyncpg://app:app@localhost:5433/desafio_test
pytest -v
ruff check .

# frontend (Vitest + Testing Library, no network)
cd frontend && npm test
```

The suite runs against a **separate** database (`desafio_test`): it creates the tables once per
session, drops them at the end and truncates them after every test, and it refuses to start if
`TEST_DATABASE_URL` is unset or equal to `DATABASE_URL`. An autouse fixture forces
`pydantic_ai.models.ALLOW_MODEL_REQUESTS = False`, so no test can reach a real LLM. Every test gets a fresh `fakeredis`, and a file lock in `conftest.py` makes a second
run on the same test database wait for the first one instead of wiping its rows.

Frontend:

```bash
cd frontend
cp .env.example .env               # VITE_API_URL=http://localhost:8000
npm install
npm run dev                        # http://localhost:5173
```

## Chat: history, `list_tasks` and streaming

- **History.** `conversation_id` (UUID) is optional in the chat body; the server generates one when missing and returns it. The PydanticAI-serialized conversation lives **only in Redis** at `chat:{user_id}:{conversation_id}`, TTL `CHAT_HISTORY_TTL_SECONDS` (default 24 h). Only the last `CHAT_HISTORY_MAX_MESSAGES` (default 20) messages go back to the model, always cut at a user turn so a tool call is never split from its return. The client never sends history. Another user's `conversation_id` misses (the key carries the JWT `user_id`) and starts a new conversation. Redis down: the chat continues without history and logs `cache_degraded`. Messages never reach Postgres.
- **What the model gets.** The static `SYSTEM_PROMPT`, that trimmed history and the new message. Tasks only enter through `list_tasks` (same `task_service` as the API, no `user_id` argument, `status`/`priority` filters, at most 10 results with `id`, `title`, `status`, `priority`, `department`) or `search_task_memory` (read-only topic search over the user's own tasks: `query` up to 200 chars, optional `status`, `limit` up to 5; returns `task_id`, `title`, `status`, `priority`, `department` and up to 160 chars of description; no `user_id` in the schema).
- **Streaming.** `POST /v1/chat/stream` (same body, authenticated) answers `text/event-stream` with `data: <json>` events: `{"type":"meta","conversation_id"}`, then `{"type":"delta","text"}`, then `{"type":"done","reply","created_task"|null,"conversation_id"}` or `{"type":"error","detail"}`. Built on `agent.run_stream_events`; the DB session is opened inside the generator (through the same, overridable `get_db`), committed once after a successful run, and the task list is invalidated after the commit.

## Task search index (hybrid retrieval)

- `task_search_index` is a **derived projection** of each task (one row per `user_id + task_id`, removed by `ON DELETE CASCADE`). Its content comes only from title, description, department, priority and status; chat and AI answers never enter the corpus.
- Indexing runs in `task_service` on create and update (API and chat tool alike). `source_hash` (sha256) skips re-embedding when nothing changed. If embedding fails the task is still saved and the row has no vector (`task_embedding_failed` log).
- `retrieve_related_tasks` ([app/services/task_retrieval.py](app/services/task_retrieval.py)) filters by `user_id` in SQL and fuses two channels with RRF (k=60), up to 20 candidates each: Postgres full-text (`to_tsvector('simple', ...)` + `ts_rank`, GIN index, always on) and cosine similarity over embeddings of the same model. Each result keeps its origin (`lexical`, `vector`, `both`) and scores.
- **No pgvector**: vectors are stored as `ARRAY(float)` and cosine is computed in Python over the user's tasks. Fine at challenge scale, not for large corpora.
- Configuration: `EMBEDDING_MODEL` (any PydanticAI embedding model, e.g. `openai:text-embedding-3-small`). Empty or `none` (default) = lexical only, no key. Each row records the model that produced its vector. Run the seed (idempotent) to index existing tasks.
- **Re-ranking.** `retrieve_and_rerank` takes up to 20 RRF candidates, reorders them and returns at most 5: `rerank_score = rrf/rrf_max + 0.15·same department + 0.10·recency + 0.05·same priority`, `recency = 1/(1 + days since updated_at/30)`. RRF dominates; the rest breaks ties. `rerank_score` is its own field; per-channel scores are kept. If the reranker fails, the RRF order is used (`rerank_failed` log).
- **Assistant context.** Two separate blocks: `<related_tasks>` (up to 5 relevant open tasks, current work) and `<completed_tasks>` (up to 5 similar completed tasks, episodic memory), each item `[task_id] title | status | priority | department`, query = the task's title + description + department, the task itself excluded. If retrieval fails (or finds no open task), open tasks fall back to the same department and completed to empty. The assistance cache key is `assist:{user_id}:{task_id}:{updated_at}:{list version}`, so any task write of the user invalidates it.
- **Eval** ([docs/retrieval-eval.md](docs/retrieval-eval.md)): 12 queries over 18 tasks of two users, deterministic fake embedder. RRF Recall@5 1.000 / MRR@5 1.000; reranked Recall@5 1.000 / MRR@5 1.000. The set saturates, so this shows the rerank does not hurt, not that it helps. The test fails if Recall@5 drops or if embedding/rerank degrade during the run.

## Project Structure

```
app/
├── main.py                  # FastAPI entrypoint: setup_logging, CORS, 404/503 handlers
├── config.py                # Settings (pydantic-settings)
├── api/
│   ├── deps.py              # get_db · get_current_user (uniform 401)
│   └── v1/
│       ├── router.py        # Route aggregator (/v1 prefix)
│       └── endpoints/       # auth.py · tasks.py · chat.py
├── core/
│   ├── database.py          # AsyncEngine and session factory
│   ├── security.py          # JWT and password hashing (bcrypt)
│   ├── cache.py             # Best-effort Redis (a failure is a cache miss, never an outage)
│   └── logging.py           # setup_logging() + JsonFormatter
├── models/                  # User · Task · TaskSearchIndex (SQLAlchemy 2.0, Mapped[...])
├── schemas/                 # auth · task · chat · assistance (Pydantic v2)
├── repositories/            # Queries, always scoped by user_id
├── services/                # task_service · task_assistant_service · task_retrieval (hybrid search + rerank)
└── agent/
    ├── agent.py             # Chat agent (create_task, list_tasks, search_task_memory)
    ├── history.py           # Chat history in Redis, bounded and with a TTL
    ├── task_assistant.py    # Assistant, output_type=TaskAssistance
    ├── tools.py             # Chat tools (user_id always from ctx.deps)
    ├── prompts.py           # Static prompts of both agents
    └── deps.py              # AgentDeps · AssistantDeps · 503 exceptions
frontend/
└── src/
    ├── api/                 # client.ts (ApiError) · auth · tasks · chat
    ├── pages/               # LoginPage · TasksPage (single 401 logout seam)
    ├── components/          # AppHeader, TaskForm, TaskFilters, TaskList, KanbanBoard, TaskCalendar, ChatPopup, ChatPanel, TaskAssistantPanel, Badge…
    ├── test/                # Vitest + Testing Library (login, list states, filters, SSE chat)
    └── types.ts             # Types mirroring the API schemas
tests/                       # auth, tasks, isolation, chat, history, cache, assistant, RAG, retrieval eval
docs/                        # retrieval-eval.md (Recall@5 / MRR@5)
seed/                        # seed_data.py (idempotent, 2 users)
```

## Submission

1. Create a **public** GitHub repository from this project.
2. Update this README with:
   - the **seed credentials**;
   - your **questionnaire answers**;
   - the decisions you made and anything left out (if applicable).
3. Send us the repository link.

### Checklist

- [x] JWT authentication (register, login, me)
- [x] Task CRUD with per-user isolation
- [x] Alembic migration
- [x] PydanticAI agent with the `create_task` tool
- [x] Task assistant with structured output and context explained in the README
- [x] Frontend: login, list, create, actions, chat and AI help
- [x] Automated tests (including chat and assistant with `TestModel`)
- [x] Structured logs
- [x] Seed with documented credentials
- [x] Questionnaire answered

Nice to have:

- [x] `list_tasks` tool (and `search_task_memory`)
- [x] Assistant evaluation cache (Redis)
- [x] Conversation history (`message_history` in Redis) and streaming chat
- [x] List filters (`status`, `priority`, `skip`/`limit`)
- [x] Redis cache for the task list, with invalidation
- [x] Frontend tests (Vitest + Testing Library)
- [ ] `BackgroundTasks` audit log
- [ ] React Query or a state manager
- [ ] CI pipeline

Good luck! 🚀

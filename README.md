# Desafio Técnico — Desenvolvedor(a) FullStack Júnior (Foco em Backend · Python / AI)

> 🇺🇸 English version: [README.en-us.md](README.en-us.md)

## Objetivo

Você vai construir um **gerenciador de tarefas com assistente de IA**: cada usuário faz login, gerencia as próprias tarefas por uma interface React, pode pedir a um agente de IA, em linguagem natural, que cadastre tarefas por ele, e pode pedir à IA que **avalie uma tarefa e monte um plano para executá-la**.

O foco do desafio é o **backend**. Queremos avaliar sua capacidade de construir uma API limpa, validada e bem organizada, além de integrar um agente de IA a um fluxo real do produto. O frontend é mais simples e serve para mostrar que você sabe consumir a sua própria API.

Não esperamos um sistema perfeito. Preferimos **código simples, legível e bem explicado** a muitas funcionalidades pela metade. Se não conseguir terminar algo, conte no README o que faltou e como você faria.

## Stack Tecnológica

| Camada | Tecnologias |
|---|---|
| Linguagem | Python 3.11+ (`async`/`await` e type hints) |
| Framework Web | FastAPI (rotas assíncronas, `Depends`, Swagger automático) |
| Validação | Pydantic v2 |
| IA | PydanticAI (agente + tool calling) |
| Banco de Dados | PostgreSQL + SQLAlchemy 2.0 (assíncrono) + Alembic |
| Frontend | React + TypeScript (Vite). **Next.js também é aceito** |
| Infra | Docker e Docker Compose |
| Padrões | PEP8 (ruff), código e logs em inglês, commits padronizados |

## O que já vem pronto

Para você focar no que importa, o repositório já traz:

- ✅ **Docker Compose** com API, PostgreSQL e frontend (`docker compose up --build`)
- ✅ **Configurações** tipadas com `pydantic-settings` ([app/config.py](app/config.py))
- ✅ **Conexão assíncrona com o banco** ([app/core/database.py](app/core/database.py)) e dependência `get_db()` ([app/api/deps.py](app/api/deps.py))
- ✅ **Utilitários de segurança**: hash de senha (bcrypt) e criação/validação de JWT ([app/core/security.py](app/core/security.py))
- ✅ **Model `User`** pronto, para servir de referência ([app/models/user.py](app/models/user.py))
- ✅ **Alembic** configurado e um **router** v1 já registrado
- ✅ **Cliente HTTP de testes** (`async_client`) e um teste de exemplo ([tests/](tests/))
- ✅ **Esqueleto do frontend** em React + TypeScript que já compila, com cliente HTTP, telas e componentes ([frontend/](frontend/))

Cada arquivo que você precisa completar tem um comentário no topo com **"You should implement here"** explicando o que é esperado.

> **Nota:** esta seção e a de **Escopo do Desafio** abaixo são o enunciado original, escrito para quem ia implementar o desafio. Elas falam de `TODO`s e dos comentários "You should implement here" que **não existem mais** no código: tudo o que era obrigatório foi implementado. O que foi entregue de fato está descrito em [Como Executar](#como-executar), [Como rodar os testes](#como-rodar-os-testes), [Contexto enviado a cada agente](#contexto-enviado-a-cada-agente), [Decisões e o que ficou de fora](#decisões-e-o-que-ficou-de-fora) e [Estrutura do Projeto](#estrutura-do-projeto).

## Escopo do Desafio

### Parte 1: Autenticação e CRUD de Tarefas (obrigatório)

1. **Autenticação JWT**
   - `POST /v1/auth/register`: cria um usuário (senha armazenada com hash).
   - `POST /v1/auth/login`: valida as credenciais e retorna um token JWT.
   - `GET /v1/auth/me`: retorna o usuário autenticado.
   - Implemente a dependência `get_current_user()` em [app/api/deps.py](app/api/deps.py).

2. **CRUD de Tarefas** (`/v1/tasks`)
   - Criar, listar, buscar por ID, atualizar parcialmente (`PATCH`) e excluir.
   - Campos: `title`, `description`, `status` (`pending` / `in_progress` / `completed`), `priority` (`low` / `medium` / `high` / `urgent`), `department`, `created_at` e `updated_at`.
   - Validação com **schemas Pydantic v2** e `response_model` nas rotas.

3. **Isolamento por usuário** 🔒
   - Cada tarefa pertence a um usuário (`user_id`).
   - Um usuário **nunca** pode ver, alterar ou excluir tarefas de outro usuário. Acessar a tarefa de outro usuário deve retornar `404`.

4. **Banco de dados**
   - Model `Task` com SQLAlchemy 2.0 (estilo `Mapped[...]`).
   - Pelo menos **uma migration Alembic** criando as tabelas.

### Parte 2: Agente de IA com PydanticAI (obrigatório)

1. **Endpoint `POST /v1/chat`** (autenticado): recebe a mensagem do usuário e retorna a resposta do agente.
2. **Agente PydanticAI** com um system prompt claro ([app/agent/](app/agent/)).
3. **Tool `create_task`**: o agente extrai as informações da mensagem, valida com o schema Pydantic `TaskCreate` e cria a tarefa no banco **para o usuário logado**.

**Cenário esperado:** ao enviar *"Cadastre uma tarefa urgente chamada 'Revisar relatório financeiro' para o departamento Comercial"*, deve surgir uma tarefa com `priority=urgent` e `department=Comercial` para o usuário autenticado.

4. **Tratamento de erros:** se o provedor da LLM falhar, a API deve responder com um erro controlado (ex.: `503`), e não com um erro 500 genérico.

> 💡 **Você não precisa pagar por uma API de LLM.** Escolha uma opção no `.env`:
> - `LLM_MODEL=test`: modelo falso do PydanticAI, sem chave. Ele chama suas tools com dados fictícios, o que é ótimo para desenvolver.
> - `LLM_MODEL=ollama:llama3.2`: LLM local e gratuito via [Ollama](https://ollama.com).
> - `LLM_MODEL=google:gemini-3.8-flash`: Gemini, que tem plano gratuito.
> - `LLM_MODEL=openai:<modelo>`: OpenAI.
>
> Nos **testes automatizados**, use o `TestModel` do PydanticAI (veja [tests/conftest.py](tests/conftest.py)). Os testes não devem chamar uma LLM real.

### Parte 3: Assistente de Tarefas com IA (obrigatório)

Além de criar tarefas, a IA deve **ajudar o usuário a executá-las**. Nesta parte avaliamos principalmente como você trabalha com **contexto**: que informações a LLM recebe, de onde elas vêm e o que fica de fora.

1. **Endpoint `POST /v1/tasks/{task_id}/assist`** (autenticado): a IA avalia a tarefa e retorna um plano.
2. **Um segundo agente PydanticAI** ([app/agent/task_assistant.py](app/agent/task_assistant.py)), separado do agente do chat, com **saída estruturada** (`output_type`) usando o schema `TaskAssistance` ([app/schemas/assistance.py](app/schemas/assistance.py)):
   - resumo da tarefa e complexidade (`low` / `medium` / `high`);
   - estimativa de esforço em horas;
   - prioridade sugerida, com justificativa (a prioridade atual faz sentido?);
   - passos concretos e ordenados para executar a tarefa;
   - riscos e pontos de atenção;
   - perguntas de esclarecimento, quando faltar informação.
3. **Montagem do contexto** ([app/services/task_assistant_service.py](app/services/task_assistant_service.py)):
   - a tarefa é buscada no banco **filtrando pelo usuário logado** (tarefa de outro usuário retorna `404`);
   - inclua um contexto complementar **pequeno e relevante**, por exemplo até 5 outras tarefas abertas do mesmo usuário e do mesmo departamento;
   - injete esse contexto via **instruções dinâmicas** (`@agent.instructions` + `RunContext`), separado do prompt fixo;
   - não envie dados desnecessários ou sensíveis à LLM (hash de senha, e-mail, dados de outros usuários, a tabela inteira).
4. Se a tarefa tiver pouca informação (ex.: sem descrição), a IA deve **dizer isso e fazer perguntas**, em vez de inventar detalhes.
5. **Explique no README** quais informações você enviou à LLM e por quê.

### Parte 4: Frontend React (obrigatório)

O esqueleto já está em [frontend/](frontend/). Complete os pontos marcados com `TODO` *(todos os seis itens abaixo estão implementados)*:

1. **Tela de login** que salva o token e mostra os erros.
2. **Lista de tarefas** do usuário, com estados de carregando, vazio e erro.
3. **Formulário** para criar tarefas.
4. **Ações** para alterar o status e excluir tarefas.
5. **Painel de chat** com o agente de IA. Quando o agente criar uma tarefa, a lista deve ser atualizada.
6. Botão **"Pedir ajuda à IA"** em cada tarefa, abrindo o painel [TaskAssistantPanel](frontend/src/components/TaskAssistantPanel.tsx) com a avaliação e o plano de execução.

No backend, configure o **CORSMiddleware** para que o frontend consiga chamar a API. *(Feito: o `CORSMiddleware` está em [app/main.py](app/main.py), com as origens vindas de `settings.cors_origins_list` — nunca `"*"`.)*

Não avaliamos design. Avaliamos **consumo da API, gerenciamento de estado e organização dos componentes**. Pode usar qualquer biblioteca (Tailwind, MUI, React Query etc.). Se preferir **Next.js**, pode substituir a pasta `frontend/`, desde que o projeto continue rodando pelo Docker Compose.

### Parte 5: Qualidade e padrões (obrigatório)

- **Testes automatizados** (pytest): pelo menos login, CRUD, isolamento entre usuários, chat e assistente de tarefas (com `TestModel`). Os arquivos em [tests/](tests/) listam os cenários sugeridos.
- **Logs estruturados** (JSON ou chave=valor) em [app/core/logging.py](app/core/logging.py). Registre pelo menos a criação de tarefas e as chamadas ao agente.
- **Documentação da API**: docstrings nas rotas e `summary`/`description` quando fizer sentido. Lembre que o Swagger é gerado a partir delas.
- **Seed** com pelo menos 2 usuários e algumas tarefas ([seed/seed_data.py](seed/seed_data.py)). Informe as credenciais no README.
- **Commits** pequenos e com mensagens claras, seguindo o padrão [Conventional Commits](https://www.conventionalcommits.org/pt-br/) (ex.: `feat: add task CRUD endpoints`), em branches no estilo git flow (`feature/...`).
- Código passando no `ruff check .`.

### Diferenciais (opcionais)

Só faça estes itens depois de concluir o obrigatório. Eles **não são necessários** para ser aprovado.

> **Feitos neste projeto:** tool `list_tasks`, cache da avaliação, histórico da conversa, filtros na listagem, Redis como cache da listagem, testes no frontend e chat com streaming. Também foi feito um diferencial próprio, a busca nas tarefas do usuário (RAG). Ficaram de fora: `BackgroundTasks`, React Query e CI.

- Tool extra no agente, por exemplo `list_tasks` (*"quais são minhas tarefas urgentes?"*).
- Cache da avaliação do assistente, para não chamar a LLM de novo enquanto a tarefa não mudar.
- Perguntas de acompanhamento sobre a mesma tarefa, mantendo o histórico da conversa (`message_history`).
- Filtros e paginação na listagem de tarefas.
- **BackgroundTasks** do FastAPI para registrar um log de auditoria quando uma tarefa for criada.
- **Redis** como cache da listagem de tarefas, com invalidação ao criar, editar ou excluir.
- Testes no frontend (Vitest + Testing Library).
- Uso de React Query ou de um gerenciador de estado.
- Pipeline de CI (GitHub Actions) rodando lint e testes.

## Critérios de Avaliação

| Critério | Peso | O que observamos |
|---|---|---|
| Backend: API e dados | 30% | Rotas assíncronas, uso de `Depends`, schemas Pydantic, models, migration, separação em camadas (rota → service → repository) |
| Agentes de IA e contexto | 25% | Organização dos agentes, clareza dos prompts, tool validada com Pydantic, saída estruturada, escolha e montagem do contexto, tratamento de erros da LLM |
| Segurança | 15% | JWT, senhas com hash, isolamento entre usuários |
| Frontend | 15% | Consumo da API, estados de carregando/erro, organização dos componentes |
| Qualidade | 15% | Testes, legibilidade, logs, README, histórico de commits |

## Questionário Técnico

Responda com suas palavras, de forma curta e direta. Não existe resposta única certa: queremos entender o seu raciocínio.

### 1. Async no FastAPI

Qual a diferença entre declarar uma rota com `async def` e com `def` no FastAPI? Em que situação usar `async def` pode **piorar** a performance?

**Resposta:**

Uma rota `async def` é executada **no próprio event loop**: enquanto ela está em um `await`, o loop atende outras requisições. Uma rota `def` é síncrona e o FastAPI a executa **em um threadpool** (via AnyIO), justamente para que o código bloqueante dela não pare o loop.

`async def` piora a performance quando há **trabalho bloqueante dentro da corrotina**: um driver síncrono (`psycopg2`), `requests`, `time.sleep`, leitura de arquivo ou CPU pesada. Nesse caso nada libera o loop, e uma única requisição lenta congela *todas* as outras — a mesma função declarada como `def` seria pior em overhead, mas ficaria isolada em uma thread.

Neste projeto o caminho de I/O é assíncrono de ponta a ponta: `asyncpg` + `AsyncSession`, toda query com `await` nos repositories, e as chamadas à LLM com `await agent.run(...)`. Nenhuma função de `app/repositories/` ou `app/services/` faz I/O síncrono.

A exceção honesta é o `bcrypt` em `app/core/security.py`: `hash_password` e `verify_password` são síncronos e gastam ~100 ms de CPU dentro das rotas `async def` de `register` e `login`, ou seja, bloqueiam o loop por esse tempo. Para o volume deste desafio é aceitável e mantém o código simples; sob carga real o certo seria mandá-los para um thread (`anyio.to_thread.run_sync`) — é a mesma correção dos dois lados, já que o `login` paga um bcrypt mesmo quando o e-mail não existe (equalização de timing).

### 2. Fluxo do agente

Descreva, passo a passo, o que acontece desde o momento em que o usuário envia a mensagem no chat até a tarefa ser salva no banco. Onde entra a validação do Pydantic nesse fluxo?

**Resposta:**

1. `POST /v1/chat` chega com o header `Authorization: Bearer <jwt>`.
2. `get_current_user` ([app/api/deps.py](app/api/deps.py)) decodifica o token, carrega o usuário e devolve um `User`. Qualquer falha é o **mesmo 401**.
3. **Validação Pydantic nº 1 (entrada do usuário):** o corpo é validado contra `ChatRequest` ([app/schemas/chat.py](app/schemas/chat.py)); mensagem vazia ou longa demais nunca chega ao agente (422).
4. A rota monta `AgentDeps(db=..., user_id=current_user.id)` e chama `await agent.run(message, deps=deps, usage_limits=UsageLimits(request_limit=5, tool_calls_limit=3))` — o limite evita que um loop de tool calls rode indefinidamente.
5. O modelo decide chamar a tool `create_task_tool` e emite os argumentos.
6. **Validação Pydantic nº 2 (saída do modelo):** a PydanticAI valida os argumentos contra a assinatura da tool ([app/agent/tools.py](app/agent/tools.py)), que declara `title`, `department`, `priority` (enum `TaskPriority`) e `description` com `Annotated[..., Field(...)]`. Argumento inválido volta ao modelo como erro de validação, para ele corrigir e tentar de novo.
7. **Validação Pydantic nº 3 (portão de domínio):** a tool constrói `TaskCreate(...)` — é aqui que valem os limites de tamanho e os enums do domínio. Se algo escapar do passo anterior, vira um `ModelRetry` com a lista de campos errados, não um 500.
8. `task_service.create_task(ctx.deps.db, ctx.deps.user_id, data)` cria a `Task` com o `user_id` vindo **das deps**, faz `flush` (sem commit) e registra o log `task_created`.
9. Terminada a run, a rota lê a tarefa criada (o flush já populou os defaults), faz **um** `commit` e devolve `ChatResponse(reply=..., created_task=...)`, serializado por `response_model`.
10. Qualquer exceção no caminho (provedor fora do ar, estouro de `UsageLimits`, erro na tool, falha no commit) faz `rollback`, loga `chat_agent_failed` com o tipo do erro e responde **503** com um detalhe fixo — uma run que falhou não deixa tarefa pela metade no banco.

Com os diferenciais, dois detalhes entram nesse fluxo: antes do passo 4 a rota carrega do Redis o histórico da conversa (`chat:{user_id}:{conversation_id}`, nunca enviado pelo cliente) e o passa como `message_history`; depois do commit ela salva a conversa de volta e invalida o cache da lista. `POST /v1/chat/stream` segue os mesmos passos, mas entrega o texto em eventos SSE enquanto o modelo gera, e o commit continua único, só depois de o run terminar.

Os dois pontos que o desafio pede estão nos passos 3 e 6/7: o Pydantic valida o que **o usuário** enviou e, depois, o que **o modelo** gerou. O segundo é o que importa para segurança: a saída de uma LLM é entrada não confiável.

### 3. Contexto do assistente

Quais informações você enviou à LLM no assistente de tarefas e o que decidiu deixar de fora? Como essa escolha afeta a qualidade da resposta, o custo (tokens) e a privacidade do usuário?

**Resposta:**

O modelo recebe o prompt fixo e, por requisição, **a tarefa em análise**: título, descrição (ou um "não informada" explícito), departamento, status e prioridade. O texto livre vai dentro de um bloco `<task>` que o prompt declara ser dado, nunca instrução, e os sinais `<` e `>` são substituídos nesses campos para que ninguém consiga forjar ou fechar a tag.

Junto vão dois conjuntos curtos, recuperados por relevância **só entre as tarefas do próprio usuário** (busca híbrida + re-ranking, ver [Índice de busca](#índice-de-busca-das-tarefas-busca-híbrida)):

- `<related_tasks>`: **até 5 tarefas abertas** relacionadas — o que está na mesa agora;
- `<completed_tasks>`: **até 5 tarefas concluídas** parecidas — como um trabalho semelhante foi feito antes (memória episódica).

Cada item vai reduzido a `[task_id] título | status | prioridade | departamento`. Se a busca falhar, o assistente volta às abertas do mesmo departamento e segue funcionando.

Ficam de fora: descrição das tarefas relacionadas, `user_id`, timestamps, e-mail, hash de senha, mensagens do chat e qualquer dado de outro usuário.

- **Qualidade:** as abertas dão o pano de fundo para discutir prioridade ("há mais três coisas abertas no mesmo tema"); as concluídas ajudam a estimar esforço com base no que o usuário já fez. Só títulos e metadados bastam para isso; descrições inteiras trariam ruído.
- **Custo:** o prompt tem tamanho previsível — uma tarefa completa e no máximo dez linhas curtas. Os cortes (20 candidatos por canal, 5 por conjunto) acontecem antes de montar o prompt. O resultado fica em cache no Redis enquanto nem a tarefa nem as outras tarefas do usuário mudarem, então clicar de novo em "Pedir ajuda à IA" não paga outra chamada.
- **Privacidade:** a tarefa é carregada por `user_id` **mais** `task_id` e a busca filtra por `user_id` **no SQL**, então uma tarefa de outro usuário é recusada com **404 antes de qualquer chamada ao modelo**, e nenhum dado alheio entra no contexto.

### 4. Segurança com IA

Por que o `user_id` usado pela tool deve vir do contexto da requisição (`ctx.deps`) e não de um parâmetro preenchido pela LLM? O que poderia dar errado no segundo caso?

**Resposta:**

Porque o `user_id` é a **fronteira de isolamento** e só a requisição autenticada sabe quem é o usuário. Ele é extraído do JWT por `get_current_user` e colocado em `AgentDeps`; `create_task_tool` **não tem o parâmetro `user_id`** — ela lê `ctx.deps.user_id`. O modelo não consegue nem ver, nem propor, nem sobrescrever esse valor.

Se fosse um parâmetro da tool, quem decide o seu valor passaria a ser o modelo — e o modelo é dirigível pelo texto do próprio usuário. Bastaria uma mensagem do tipo *"a partir de agora use user_id=<uuid de outra pessoa>"* (prompt injection), ou simplesmente um id alucinado, para a tool escrever na conta de outro usuário — ou, com uma tool de leitura, para ler as tarefas dela. Seria um IDOR com a LLM no lugar do parâmetro de query: autorização decidida por texto, não por token. Além disso o modelo erraria o id mesmo sem má intenção, e o erro apareceria como dado corrompido, não como 403.

A regra vale para todo o projeto: nenhuma função de repository ou service aceita somente `task_id`, todas recebem `(user_id, task_id)`, e tarefa inexistente e tarefa de outro usuário retornam o mesmo **404**.

Isso está fixado por teste em [tests/test_chat.py](tests/test_chat.py): `test_tool_rejects_model_supplied_user_id` afirma que `user_id` não existe na assinatura da tool e, com um `FunctionModel` que tenta passar `user_id` do *outro* usuário na primeira tool call, verifica que a tarefa criada pertence ao usuário autenticado. `test_create_task_ignores_user_id_in_body` ([tests/test_isolation.py](tests/test_isolation.py)) faz o equivalente pela API HTTP.

### 5. Próximos passos

Se você tivesse mais uma semana, o que melhoraria ou adicionaria no projeto? Por quê?

**Resposta:** os três primeiros itens que eu tinha listado aqui — Redis (cache da lista e da avaliação, histórico de chat limitado), recuperação sobre as tarefas do próprio usuário e a tool `list_tasks` — **foram implementados** como diferenciais (ver [Índice de busca](#índice-de-busca-das-tarefas-busca-híbrida) e [Contexto enviado a cada agente](#contexto-enviado-a-cada-agente)). Com mais uma semana, em ordem de valor:

1. **Avaliar a busca com um modelo de embedding real.** A avaliação atual usa um embedder falso e satura (Recall@5 e MRR@5 = 1,000 antes e depois do re-ranking), então prova que o re-ranking não piora, não que melhora. Eu aumentaria o dataset com consultas mais difíceis e mediria com um modelo real antes de mexer nos pesos.
2. **Tirar o bcrypt do event loop** (`anyio.to_thread.run_sync`), como expliquei na resposta 1, e um teste de carga simples para comprovar.
3. **CI (GitHub Actions)** rodando `ruff`, `pytest` (com Postgres e Redis de serviço) e os testes do frontend em cada PR.
4. **pgvector** no lugar do cosseno em Python, se o número de tarefas por usuário crescer.
5. **`BackgroundTasks` para log de auditoria** na criação de tarefa, o único diferencial do README que ficou de fora.

## Como Executar

### Pré-requisitos

- Docker e Docker Compose
- (Opcional) Python 3.11+ e Node.js 20+ para rodar fora do Docker

### Com Docker Compose (recomendado)

```bash
cp .env.example .env
docker compose up --build
```

| Serviço | URL |
|---|---|
| API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| Frontend | http://localhost:5173 |
| PostgreSQL | `localhost:5433` (mude com `POSTGRES_HOST_PORT` se a porta estiver ocupada) |
| Redis | `localhost:6379` (mude com `REDIS_HOST_PORT` se a porta estiver ocupada) |

Com os containers no ar, aplique a migration e carregue o seed (**é isso que cria os usuários de teste**):

```bash
docker compose exec api alembic upgrade head
docker compose exec api python -m seed.seed_data
```

Outros comandos úteis:

```bash
docker compose exec api ruff check .
docker compose exec -e TEST_DATABASE_URL=postgresql+asyncpg://app:app@db:5432/desafio_test api pytest -v
```

> Os testes precisam de um banco **separado** (veja [Como rodar os testes](#como-rodar-os-testes)); crie-o uma vez com
> `docker compose exec db createdb -U app desafio_test`.

### Credenciais do seed

| E-mail | Senha |
|---|---|
| `ana@example.com` | `password123` |
| `bruno@example.com` | `password123` |

```bash
# dentro do Docker
docker compose exec api python -m seed.seed_data
# localmente (com as variáveis da seção "Localmente" exportadas)
python -m seed.seed_data
```

Cada usuário recebe 5 tarefas, com status, prioridades e departamentos diferentes. São dois usuários para dar para **ver** o isolamento (entre com um e com o outro: as listas não se cruzam) e cada um tem **mais de uma tarefa aberta no mesmo departamento**, que é o que faz o contexto de tarefas relacionadas do assistente aparecer. Duas tarefas (uma por usuário) estão **sem descrição** de propósito, para mostrar o assistente dizendo que falta informação e devolvendo perguntas em vez de inventar.

O seed é **idempotente**: ele procura o usuário pelo e-mail e a tarefa por `(user_id, title)`, então rodar duas vezes não duplica nada e não quebra.

### Localmente (sem Docker para a API)

```bash
# 1. Suba só o banco e o Redis (localhost:5433 e localhost:6379;
#    mude com POSTGRES_HOST_PORT / REDIS_HOST_PORT se a porta estiver ocupada)
docker compose up db redis -d --wait

# 2. Crie o banco de testes (uma vez só)
docker compose exec db createdb -U app desafio_test

# 3. Ambiente Python
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt

# 4. Aponte as URLs para a porta exposta, só nesta shell
#    (não edite o .env — veja a nota abaixo)
export DATABASE_URL=postgresql+asyncpg://app:app@localhost:5433/desafio
export TEST_DATABASE_URL=postgresql+asyncpg://app:app@localhost:5433/desafio_test
export REDIS_URL=redis://localhost:6379/0   # a porta de REDIS_HOST_PORT, se você mudou
export PYDANTIC_AI_NO_BANNER=1

# 5. Migration, seed e API
alembic upgrade head
python -m seed.seed_data
uvicorn app.main:app --reload
```

**Por que exportar em vez de editar o `.env`:** o `.env` é o arquivo que o `docker compose` entrega ao container, e lá dentro o banco se chama `db:5432`. Se você trocar o `DATABASE_URL` do `.env` para `localhost:5433`, o container da API para de achar o banco. Variável de ambiente ganha do `.env` no `pydantic-settings`, então exportar na shell resolve o caso local sem quebrar o caso Docker, e o mesmo `.env` serve para os dois: `DATABASE_URL` é o banco da aplicação (`desafio`) e `TEST_DATABASE_URL` é o banco exclusivo da suíte (`desafio_test`). O `REDIS_URL` segue a mesma regra (`redis:6379` dentro do Docker, `localhost` fora). Sem ele a API funciona, mas sem cache e sem histórico do chat, e registra `cache_degraded` no log.

Para não repetir isso toda vez, salve essas linhas `export` em um arquivo `.dev-env.sh` (ele está no `.gitignore`, é só para a sua máquina) e use `source .dev-env.sh` antes de `pytest`, `alembic`, `uvicorn` e do seed.

Frontend:

```bash
cd frontend
cp .env.example .env               # VITE_API_URL=http://localhost:8000
npm install
npm run dev                        # http://localhost:5173
```

Entre com uma das credenciais do seed e você já cai na lista de tarefas, com o chat e o botão "Pedir ajuda à IA" funcionando. Com `LLM_MODEL=test` (o padrão) os dois agentes respondem com o modelo falso da PydanticAI, sem chave de API: o chat cria uma tarefa com dados fictícios e o assistente devolve um `TaskAssistance` fictício, o que é suficiente para ver o fluxo de ponta a ponta. Para respostas de verdade, escolha um provedor no `.env` (`LLM_MODEL=ollama:llama3.2`, `google:gemini-3.8-flash` etc.).

## Como rodar os testes

```bash
export TEST_DATABASE_URL=postgresql+asyncpg://app:app@localhost:5433/desafio_test
pytest -v
ruff check .

# frontend
cd frontend && npm test
```

O banco `desafio_test` precisa existir (`docker compose exec db createdb -U app desafio_test`, uma vez só).

- **Banco separado.** A suíte roda em `desafio_test`, nunca no banco da aplicação — [tests/conftest.py](tests/conftest.py) aborta na hora se `TEST_DATABASE_URL` estiver vazio **ou** igual a `DATABASE_URL`, porque ele apaga as tabelas no fim. As tabelas são criadas uma vez por sessão com `Base.metadata.create_all`, derrubadas no fim, e **truncadas depois de cada teste**, então nenhuma linha vaza de um teste para o outro.
- **A mesma sessão em todo lugar.** `app.dependency_overrides[get_db]` devolve exatamente a `AsyncSession` que o teste usa para asserção, então o teste vê o que a requisição escreveu sem precisar de commit.
- **Nenhum teste chega a uma LLM real.** Uma fixture `autouse` força `pydantic_ai.models.ALLOW_MODEL_REQUESTS = False` durante toda a suíte. Quem esquecer de um `agent.override(model=...)` **falha com erro**, em vez de sair pela rede e gastar token. Os testes usam `TestModel` ou `FunctionModel` conforme o caso.
- **Sem Redis real.** Cada teste recebe um `fakeredis` novo e vazio; o Redis de verdade nunca é tocado, e a queda do Redis é testada com uma conexão real para uma porta fechada.
- **Uma suíte por vez.** Duas execuções ao mesmo tempo no mesmo `desafio_test` apagariam as linhas uma da outra; um lock de arquivo no `conftest.py` faz a segunda esperar a primeira terminar.

## Índice de busca das tarefas (busca híbrida)

- `task_search_index` é uma **projeção derivada** de cada tarefa (uma linha por `user_id + task_id`, removida por `ON DELETE CASCADE`). O conteúdo vem só de título, descrição, departamento, prioridade e status; chat e respostas da IA nunca entram no corpus.
- A indexação roda em `task_service` ao criar e editar (vale para a API e para a tool do chat). O `source_hash` (sha256) evita recalcular o embedding quando nada mudou. Se o embedding falhar, a tarefa é salva mesmo assim e a linha fica sem vetor (log `task_embedding_failed`).
- `retrieve_related_tasks` ([app/services/task_retrieval.py](app/services/task_retrieval.py)) filtra por `user_id` no SQL e combina dois canais com RRF (k=60), até 20 candidatos cada: full-text do Postgres (`to_tsvector('simple', ...)` + `ts_rank`, índice GIN, sempre disponível) e similaridade de cosseno sobre os embeddings do mesmo modelo. Cada resultado guarda a origem (`lexical`, `vector`, `both`) e os scores.
- **Sem pgvector**: o vetor fica em `ARRAY(float)` e o cosseno é calculado em Python sobre as tarefas do usuário. Serve para a escala do desafio, não para corpora grandes.
- Configuração: `EMBEDDING_MODEL` (qualquer modelo de embedding do PydanticAI, ex. `openai:text-embedding-3-small`). Vazio ou `none` (padrão) = só busca lexical, sem chave. Cada linha registra o modelo que gerou o vetor. Para indexar tarefas existentes, rode o seed (idempotente).
- **Re-ranking.** `retrieve_and_rerank` pega até 20 candidatos do RRF, reordena e entrega no máximo 5: `rerank_score = rrf/rrf_max + 0,15·mesmo departamento + 0,10·recência + 0,05·mesma prioridade`, com `recência = 1/(1 + dias desde updated_at/30)`. O RRF domina; o resto só desempata. O `rerank_score` é um campo próprio, os scores de cada canal ficam intactos. Se o reranker falhar, vale a ordem RRF (log `rerank_failed`).
- **Memória episódica.** Tarefas concluídas similares entram no assistente como "como trabalho parecido foi feito antes"; tarefas abertas, como contexto atual (ver abaixo).
- **Tool `search_task_memory`** (chat): somente leitura, `query` até 200 caracteres, `status` opcional, `limit` até 5; devolve `task_id`, `title`, `status`, `priority`, `department` e até 160 caracteres da descrição. Sem `user_id` no schema (argumento extra é rejeitado).
- **Avaliação** ([docs/retrieval-eval.md](docs/retrieval-eval.md)): 12 consultas sobre 18 tarefas de dois usuários (`tests/data/retrieval_eval.json`), embedder falso determinístico. RRF: Recall@5 1,000 e MRR@5 1,000; com re-ranking: Recall@5 1,000 e MRR@5 1,000. O conjunto é pequeno e já satura, então o número prova que o re-ranking não piora, não que melhora. O teste falha se o Recall@5 cair ou se embedding/reranker degradarem durante a medição.

## Contexto enviado a cada agente

São **dois agentes separados**, com prompts, deps e responsabilidades diferentes. Em nenhum dos dois o `user_id` é algo que o modelo possa ver ou escolher: ele vem do JWT, via `get_current_user`, e entra pelas deps.

### Agente do chat (`POST /v1/chat` e `POST /v1/chat/stream`)

| | |
|---|---|
| **Vai no prompt** | o prompt fixo ([app/agent/prompts.py](app/agent/prompts.py), `SYSTEM_PROMPT`: papel, quando usar cada tool, mapa de prioridade em português, "não invente título nem departamento"), o **histórico da conversa** lido do Redis (no máximo `CHAT_HISTORY_MAX_MESSAGES`, padrão 20 mensagens, cortado sempre num turno do usuário para não separar tool call de tool return) e a mensagem nova |
| **Fica de fora** | qualquer histórico enviado pelo cliente (o contrato só aceita `conversation_id`), dados de outro usuário, e-mail, hash de senha; tarefas só entram se o modelo chamar `list_tasks` ou `search_task_memory` |
| **`user_id`** | `AgentDeps.user_id`, lido pelas tools como `ctx.deps.user_id`; nenhuma tool **tem** parâmetro `user_id` |
| **Limites** | `UsageLimits(request_limit=5, tool_calls_limit=3)`; `list_tasks` devolve no máximo 10 tarefas (só `id`, `title`, `status`, `priority`, `department`, filtros `status`/`priority`); qualquer falha vira 503 (ou evento `error` no stream) com detalhe fixo |

Tools: `create_task_tool` (escreve), `list_tasks` (lê pelo mesmo `task_service` da API) e `search_task_memory` (busca por assunto nas tarefas do usuário, no máximo 5, para trabalho passado ou parecido). Elas rodam em sequência, porque dividem uma `AsyncSession`.

**Histórico.** O `conversation_id` (UUID) é opcional na requisição; se faltar, o servidor gera um e o devolve. A conversa serializada pelo PydanticAI (`ModelMessagesTypeAdapter`) fica **só no Redis**, em `chat:{user_id}:{conversation_id}`, com TTL `CHAT_HISTORY_TTL_SECONDS` (padrão 24 h). Como o `user_id` vem do JWT, o `conversation_id` de outro usuário não encontra nada e vira conversa nova. Redis fora do ar: a conversa segue sem histórico e o log registra `cache_degraded`. Mensagens e respostas nunca vão para o Postgres.

**Streaming.** `POST /v1/chat/stream` (mesmo corpo, autenticado) responde `text/event-stream`, uma linha `data: <json>` por evento:

```text
data: {"type":"meta","conversation_id":"..."}
data: {"type":"delta","text":"Tarefa "}
data: {"type":"done","reply":"Tarefa criada.","created_task":{...}|null,"conversation_id":"..."}
data: {"type":"error","detail":"The assistant is unavailable, try again later"}
```

Usa `agent.run_stream_events` (entrega texto incremental mesmo com tool call no meio). A sessão do banco é aberta **dentro do gerador** (pelo mesmo `get_db`, respeitando o override dos testes), então continua viva até o fim do stream; o commit é único, depois do run, e a lista de tarefas é invalidada depois do commit.

### Assistente de tarefas (`POST /v1/tasks/{task_id}/assist`)

| | |
|---|---|
| **Vai no prompt** | o prompt fixo (`TASK_ASSISTANT_PROMPT`) e, por instruções dinâmicas, a tarefa em análise — título, descrição (ou "não informada"), departamento dentro de um bloco `<task>`, mais status e prioridade — e dois conjuntos separados: `<related_tasks>`, **até 5** tarefas abertas relevantes (contexto atual), e `<completed_tasks>`, **até 5** concluídas similares (memória episódica). Cada item é `[task_id] título \| status \| prioridade \| departamento` |
| **Fica de fora** | descrição das tarefas relacionadas, id da própria tarefa, `user_id`, timestamps, hash de senha, e-mail e qualquer dado de outro usuário |
| **`user_id`** | a tarefa é carregada por `(user_id, task_id)` antes de qualquer chamada ao modelo (tarefa de outro usuário é 404 e o modelo nunca é chamado); os dois conjuntos vêm de `retrieve_and_rerank`, filtrado por `user_id` **no SQL**, com a própria tarefa excluída |
| **Anti-injeção** | `<` e `>` são substituídos nos campos de texto livre, então uma tarefa não consegue fechar nem forjar nenhum bloco; o prompt declara que o conteúdo dos blocos é **dado**, nunca instrução |

A query de busca é título + descrição + departamento da tarefa. Se a recuperação falhar (ou não achar nenhuma aberta, como em tarefas ainda sem índice), as abertas voltam a ser as do mesmo departamento (`list_related_open_tasks`) e as concluídas ficam vazias; o assistente não quebra. O cache da assistência usa `assist:{user_id}:{task_id}:{updated_at}:{versão da lista}`: como o contexto depende das outras tarefas, qualquer escrita do usuário (que já incrementa `tasks:version:{user_id}`) invalida a assistência; sem Redis, o cache é pulado.

## Decisões e o que ficou de fora

**Decisões**

- **Login só por form data.** `POST /v1/auth/login` recebe `application/x-www-form-urlencoded` com o e-mail no campo `username` (`OAuth2PasswordRequestForm`), não JSON. É o formato que o botão **Authorize** do Swagger usa, então o `/docs` fica utilizável sem nenhum passo manual de copiar token. `register` continua JSON.
- **401 uniforme.** `get_current_user` responde o mesmo 401 para token inválido, expirado, ilegível, usuário inexistente ou inativo. No login, um e-mail desconhecido ainda paga uma verificação de bcrypt contra um hash fixo, para que o tempo de resposta não revele quais e-mails existem.
- **404 em vez de 403.** Tarefa de outro usuário e tarefa inexistente são indistinguíveis; a decisão vive em um único `exception_handler` de `TaskNotFoundError` em [app/main.py](app/main.py). Nenhuma função de repository/service aceita somente `task_id`.
- **Listagem devolve uma lista pura**, `list[TaskResponse]`, com filtros opcionais `status`/`priority` e `skip`/`limit`. **Não** criei envelope de paginação (`{items, total, page}`) — seria mudança de contrato para um ganho que este escopo não pede; `skip`/`limit` já seguram a listagem.
- **`POST /v1/chat` sem barra no fim** (e `/v1/tasks/` com barra). Com a rota declarada como `/chat/`, o FastAPI responderia 307 para `/chat`, e um redirect quebra o preflight de CORS vindo do browser em outra origem. O CORS usa `settings.cors_origins_list`, nunca `"*"`, porque as requisições levam credencial.
- **`AgentDeps` e as exceções dos agentes moram em [app/agent/deps.py](app/agent/deps.py)**, não junto do agente, para o `app/main.py` registrar os handlers de 503 sem importar a stack de modelos da PydanticAI.
- **O teste da mensagem de referência usa `FunctionModel`, não `TestModel`.** O `TestModel` chama as tools com dados fictícios, então ele não consegue afirmar que *"Cadastre uma tarefa urgente chamada 'Revisar relatório financeiro' para o departamento Comercial"* virou `priority=urgent` + `department=Comercial`. Com `FunctionModel` eu fixo os argumentos da tool call e verifico o resto do caminho. Assumo a limitação: **esse teste cobre o caminho tool → validação → banco, não a qualidade da extração do prompt** — qualidade de prompt depende do modelo real e não é algo que eu queira travar em teste determinístico.
- **`JWT_SECRET_KEY` do `.env.example` tem 32+ bytes.** O placeholder anterior (`change-me-in-production`) tinha 23 bytes e fazia o PyJWT avisar que a chave é curta para HS256 em qualquer execução com a configuração de exemplo. Trocado pelo placeholder longo, com o comando para gerar uma chave aleatória ao lado — era o ajuste certo, em vez de silenciar o aviso dentro dos testes.

**O que ficou de fora**

- **Diferencial não implementado:** `BackgroundTasks` para log de auditoria. Redis (cache, histórico, `list_tasks`) e RAG sobre as tarefas (busca híbrida, re-ranking, memória episódica, `search_task_memory`) foram feitos.
- **RAG limitado de propósito:** só tarefas do próprio usuário; sem documentos, sem pgvector (cosseno em Python) e sem reranker por modelo (a fórmula é fixa e explicável). A avaliação é pequena e não prova ganho do re-ranking, só que ele não piora o Recall@5.
- **Testes de frontend** (Vitest/Testing Library) e **CI**: a garantia do frontend hoje é `tsc -b` + `vite build` + `oxlint`.
- **Sem React Query e sem gerenciador de estado:** React 19 puro, sem router. São duas telas; o estado cabe em `useState` e em um único ponto, em `TasksPage`, que desloga quando a API responde 401.
- **Refresh token, recuperação de senha, verificação de e-mail e rate limiting** não existem: só access token com expiração (`JWT_EXPIRATION_MINUTES`).
- **Sem `updated_at` manual, sem soft delete, sem auditoria:** `DELETE` apaga a linha.
- **Sem organizações/times/RBAC:** o isolamento é por usuário, com `user_id`. Não existe `tenant_id`.
- **O assistente não persiste nada no banco:** a avaliação fica só no cache Redis, e mensagens ou respostas da IA nunca entram no índice de busca.

## Frontend

O frontend (React 19 + TypeScript + Vite, sem router e sem biblioteca de UI ou de estado) é dividido em componentes pequenos: `AppHeader`, `TaskForm`, `TaskFilters`, `TaskList`, `TaskAssistantPanel`, `ChatPanel` e peças de apresentação (`Badge`, `EmptyState`, `ErrorState`, `Skeleton`). O estado fica em `TasksPage`: a lista, os filtros, o usuário logado (`/v1/auth/me`) e a tarefa em análise. Os filhos avisam quando algo mudou e repassam os erros da API, e um 401 sempre leva ao logout num único lugar. Os filtros de status e prioridade viram query params de `GET /v1/tasks/`, aproveitando o cache por filtro do backend; a lista recarrega a cada mudança e descarta respostas atrasadas. O chat consome `POST /v1/chat/stream` (SSE), mostra o texto enquanto chega e atualiza a lista quando o agente cria uma tarefa.

Testes: `cd frontend && npm test` (Vitest + Testing Library + jsdom, com `fetch` e a API simulados, sem rede). Cobrem o login, os estados de carregando, vazio e erro da lista, os filtros e o processamento dos eventos SSE do chat, inclusive um stream que termina sem `done`.

## Estrutura do Projeto

```
app/
├── main.py                  # Entrypoint FastAPI: setup_logging, CORS, handlers 404/503
├── config.py                # Configurações (pydantic-settings)
├── api/
│   ├── deps.py              # get_db · get_current_user (401 uniforme)
│   └── v1/
│       ├── router.py        # Agregador de rotas (prefixo /v1)
│       └── endpoints/       # auth.py · tasks.py · chat.py
├── core/
│   ├── database.py          # AsyncEngine e session factory
│   ├── security.py          # JWT e hash de senha (bcrypt)
│   ├── cache.py             # Redis best-effort (falha = cache miss, nunca derruba a API)
│   └── logging.py           # setup_logging() + JsonFormatter
├── models/                  # User · Task · TaskSearchIndex (SQLAlchemy 2.0, Mapped[...])
├── schemas/                 # auth · task · chat · assistance (Pydantic v2)
├── repositories/            # Queries, sempre com user_id
├── services/                # task_service · task_assistant_service · task_retrieval (busca híbrida + re-ranking)
└── agent/
    ├── agent.py             # Agente do chat (create_task, list_tasks, search_task_memory)
    ├── history.py           # Histórico do chat no Redis, limitado e com TTL
    ├── task_assistant.py    # Assistente, output_type=TaskAssistance
    ├── tools.py             # Tools do chat (user_id sempre de ctx.deps)
    ├── prompts.py           # Prompts fixos dos dois agentes
    └── deps.py              # AgentDeps · AssistantDeps · exceções 503
frontend/
└── src/
    ├── api/                 # client.ts (ApiError) · auth · tasks · chat
    ├── pages/               # LoginPage · TasksPage (ponto único de logout em 401)
    ├── components/          # AppHeader, TaskForm, TaskFilters, TaskList, ChatPanel, TaskAssistantPanel, Badge…
    ├── test/                # Vitest + Testing Library (login, estados da lista, filtros, chat SSE)
    └── types.ts             # Tipos espelhando os schemas da API
tests/                       # auth, tasks, isolamento, chat, histórico, cache, assistente, RAG, avaliação
docs/                        # retrieval-eval.md (Recall@5 / MRR@5)
seed/                        # seed_data.py (idempotente, 2 usuários)
```

## Entrega

1. Crie um repositório **público** no GitHub a partir deste projeto.
2. Atualize este README com:
   - as **credenciais do seed**;
   - as **respostas do questionário**;
   - as decisões que você tomou e o que ficou de fora (se for o caso).
3. Envie o link do repositório.

### Checklist

- [x] Autenticação JWT (register, login, me)
- [x] CRUD de tarefas com isolamento por usuário
- [x] Migration Alembic
- [x] Agente PydanticAI com a tool `create_task`
- [x] Assistente de tarefas com saída estruturada e contexto explicado no README
- [x] Frontend: login, lista, criação, ações, chat e ajuda da IA
- [x] Testes automatizados (incluindo chat e assistente com `TestModel`)
- [x] Logs estruturados
- [x] Seed com credenciais documentadas
- [x] Questionário respondido

Diferenciais:

- [x] Tool `list_tasks` (e `search_task_memory`)
- [x] Cache da avaliação do assistente (Redis)
- [x] Histórico da conversa (`message_history` no Redis) e chat com streaming
- [x] Filtros na listagem (`status`, `priority`, `skip`/`limit`)
- [x] Redis como cache da listagem, com invalidação
- [x] Testes no frontend (Vitest + Testing Library)
- [ ] `BackgroundTasks` para log de auditoria
- [ ] React Query ou gerenciador de estado
- [ ] Pipeline de CI

Boa sorte! 🚀

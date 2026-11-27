# Plano de execução

Este arquivo é a fonte de verdade do trabalho do desafio. A ordem abaixo protege
o prazo: primeiro entregamos todo o escopo obrigatório; depois implementamos
somente os dois diferenciais definidos neste plano.

Fonte de requisitos: `README.md`. Em caso de conflito, o obrigatório do README
vence. Os diferenciais não podem atrasar, substituir ou enfraquecer um requisito
obrigatório.

## Contrato de escopo

### Extensão autorizada: CRUD e cores do calendário

- [x] Editar campos completos e adicionar/remover prazo pelo formulário.
- [x] Duplicar dados e tags, com novo ID e status pendente.
- [x] Concluir/excluir a seleção da lista, com confirmação e falhas parciais.
- [x] Persistir tags por tarefa e validar nome, cor hexadecimal e quantidade.
- [x] Usar a primeira tag na cor do calendário e texto com contraste calculado.
- [x] Testar edição, duplicação, confirmação, parcialidade, validação e isolamento.

### Deploy de demonstração autorizado

- [x] Preparar frontend na Vercel e Dockerfile específico para Render.
- [x] Guardar quotas diárias no PostgreSQL: 10 por usuário, 50 globais por padrão.
- [x] Bloquear IA se a quota não puder ser verificada e responder 429 ao esgotar.
- [x] Aplicar limites de saída e preservar cache hits sem cobrança de quota.
- [x] Verificar 106 testes backend, 32 frontend, lint e build; construir a imagem
      de produção e confirmar a importação da API sem chamada ao provedor.
- [x] Publicar frontend na Vercel, API e datastores gratuitos no Render.
- [x] Verificar health, CORS, cadastro, login, CRUD e isolamento na API pública.
- [ ] Configurar a chave OpenAI apenas no Render e ativar o modelo real.
- [ ] Executar smoke test com modelo real nas URLs publicadas.

Extensão solicitada: prazo opcional (`due_date`, data sem horário) e calendário
mensal contendo somente tarefas com prazo da lista carregada e seus filtros.
O campo pode ser removido via PATCH com null. Google Calendar permanece fora
da implementação: OAuth por usuário, armazenamento seguro de tokens, revogação,
vínculo tarefa-evento e sincronização ampliam o escopo do desafio.

### Revisão de resiliência e interface

- [x] Isolar retrieval opcional com savepoint e testar erro SQL real.
- [x] Exigir perguntas de esclarecimento quando não houver descrição.
- [x] Versionar a chave do cache de assistência para descartar respostas antigas.
- [x] Melhorar login, hierarquia do workspace, resumo da lista, formulário e chat.
- [x] Verificar 97 testes backend, 11 frontend, lint e build.
- [ ] Inspecionar visualmente as telas no navegador.
- [ ] Validar interpretação e perguntas com um provedor LLM real.

### Fechamento da entrega com administração

- [x] Integrar e publicar a implementação na `main` do fork.
- [x] Clonar a `main` publicada e aplicar todas as migrations em banco vazio
      separado (`desafio_delivery_admin_check`).
- [x] Executar seed duas vezes nesse banco: 10 tarefas, sem duplicação.
- [x] Executar a suíte com código do clone remoto: 95 testes aprovados.
- [x] Frontend: 11 testes aprovados, lint sem avisos e build aprovado.
- [x] Disponibilizar painel administrativo para listar e ativar/desativar contas.
- [x] Testar 401/403, bloqueio de conta e impossibilidade de conceder privilégio
      pelo cadastro público.
- [x] Deixar os serviços locais ativos: frontend 5173, API 8000, Redis 6381.

Estes resultados substituem os bloqueios históricos de publicação e validação
registrados nas fases abaixo. O clone remoto foi executado usando containers
da infraestrutura local e banco de aplicação novo; não é uma nova máquina.
Provisionar administrador: `docker compose exec api python -m seed.create_admin`.

Extensão posterior autorizada: painel administrativo de contas. Cada tenant
continua sendo um usuário. Inclui listagem paginada e ativação/desativação,
permissão administrativa verificada no banco e provisionamento explícito por
CLI. Não inclui organizações, acesso administrativo a tarefas ou impersonação.

### Obrigatório

- Autenticação JWT: registro, login e usuário atual.
- CRUD assíncrono de tarefas com isolamento por usuário.
- Modelos SQLAlchemy, schemas Pydantic e migration Alembic.
- Chat autenticado com agente PydanticAI e tool `create_task`.
- Assistente de tarefas separado, com saída estruturada e contexto controlado.
- Frontend React: login, CRUD, chat e painel de assistência.
- Testes de autenticação, CRUD, isolamento, chat e assistência.
- Logs estruturados, seed, CORS, documentação e questionário técnico.

### Diferencial 1 — Redis, cache e continuidade do chat

- Cache da listagem de tarefas, isolado por usuário e filtros.
- Cache da assistência, invalidado quando a tarefa mudar.
- Histórico curto de conversa no Redis, com TTL e limite de contexto.
- Tool adicional `list_tasks`, sempre limitada ao usuário autenticado.

### Diferencial 2 — RAG e memória derivados das tarefas

- O corpus é formado exclusivamente pelas tarefas do próprio usuário.
- Tarefas abertas representam contexto operacional atual.
- Tarefas concluídas representam memória episódica do trabalho realizado.
- Busca lexical e vetorial com filtro obrigatório por `user_id`.
- Fusão dos rankings e re-ranking antes de enviar o contexto à LLM.
- Tool adicional `search_task_memory`, limitada e somente leitura.

### Fora do escopo

- Organizações, equipes, RBAC ou um novo conceito de `tenant_id`.
- Documentos externos, upload de arquivos, web search ou RAG documental.
- Respostas da IA ou mensagens do chat persistidas como memória longa.
- Redis como fonte da verdade.
- Redis para filas, sessões de autenticação ou rate limiting.
- RAG agêntico com ferramentas de escrita além de `create_task`.
- Redis Cluster, observabilidade distribuída ou infraestrutura de produção.
- React Query, paginação, filtros avançados, frontend tests e CI.
  _(Exceção posterior, a pedido do Thiago: testes de frontend com Vitest e filtros simples de status e prioridade na UI. React Query, paginação na UI e CI continuam fora.)_
- Qualquer outro item opcional do README.

`user_id` é a fronteira de isolamento. Ele sempre vem do JWT e do contexto da
requisição, nunca de argumentos produzidos pela LLM.

## Regras de execução

- [ ] Trabalhar em branches `feature/...` pequenas. _(parcial: o obrigatório inteiro (fases 0 a 7) ficou numa só branch, `feature/mandatory-scope`, com 17 commits; os diferenciais foram em branches separadas, uma por task)_
- [x] Fazer commits convencionais e focados.
- [x] Não iniciar os diferenciais antes de todo o obrigatório estar verde.
- [x] Se um diferencial ficar parcial, removê-lo da entrega em vez de manter um
      fluxo quebrado.
- [x] Escrever o teste de isolamento junto com cada acesso novo a dados.
- [x] Não chamar provedores reais nos testes automatizados.
- [x] Atualizar este arquivo ao concluir ou alterar uma decisão.

## Ordem de prioridade da avaliação

1. Backend, API e dados — 30%.
2. Agentes de IA e contexto — 25%.
3. Segurança e isolamento — 15%.
4. Frontend — 15%.
5. Qualidade, testes, logs e documentação — 15%.

Os dois diferenciais só entram depois que os cinco blocos acima estiverem
entregues e verificáveis.

## Fase 0 — Base de desenvolvimento

- [x] Usar o fork público `ThiagoEmanoel25/desafio-backend-fullstack` como
      `origin` e o repositório original como `upstream`.
- [ ] Criar a branch `feature/project-foundation`. _(não feito com esse nome: a fase 0 entrou direto na `feature/mandatory-scope`, commit `ada0f65` (`test: configure isolated async test database`); não existe branch `feature/project-foundation` no reflog local nem no remoto)_
- [x] Criar `.env` local a partir de `.env.example` sem versionar segredos.
- [x] Definir `TEST_DATABASE_URL` para um PostgreSQL separado.
- [x] Configurar fixtures assíncronas e override de `get_db`.
- [x] Bloquear chamadas reais de modelo durante os testes.
- [x] Confirmar que frontend e API compilam antes das mudanças.

Critério de conclusão:

- [x] `test_health.py` passa usando o ambiente de testes documentado.
- [x] Nenhum teste pode acessar uma LLM real.

Commit sugerido: `test: configure isolated async test database`

## Fase 1 — Domínio de tarefas e banco

- [x] Implementar `TaskStatus` e `TaskPriority` uma única vez e reutilizá-los.
- [x] Implementar `TaskCreate`, `TaskUpdate` e `TaskResponse` com
      `from_attributes=True` na resposta.
- [x] Aplicar limites de tamanho aos campos recebidos pela API e pela IA.
- [x] Implementar o model `Task` com `Mapped[...]`.
- [x] Incluir `title`, `description`, `status`, `priority`, `department`,
      `user_id`, `created_at` e `updated_at`.
- [x] Criar FK obrigatória para `users.id` e índices úteis por usuário.
- [x] Garantir `created_at` e `updated_at` no banco.
- [x] Importar `Task` em `app/models/__init__.py`.
- [x] Criar e revisar a migration de `users` e `tasks`.

Critério de conclusão:

- [x] Migration sobe e desce em um banco vazio.
- [x] Payload inválido é rejeitado antes de acessar o repositório.

Commit sugerido: `feat: add task model schemas and migration`

## Fase 2 — Autenticação JWT

- [x] Implementar `RegisterRequest`, `LoginRequest` ou formulário OAuth2,
      `TokenResponse` e `UserResponse`.
- [x] Implementar o repositório de usuários.
- [x] Implementar registro com hash bcrypt e resposta `409` para duplicidade.
- [x] Implementar login e emissão de JWT.
- [x] Implementar `get_current_user` com tratamento uniforme de `401`.
- [x] Rejeitar token inválido, expirado, usuário ausente ou inativo.
- [x] Implementar `GET /v1/auth/me`.
- [x] Adicionar summaries e response models às rotas.

Testes:

- [x] Registro bem-sucedido.
- [x] E-mail duplicado.
- [x] Login válido e senha inválida.
- [x] Token ausente, inválido e usuário inativo.

Commit sugerido: `feat: implement jwt authentication`

## Fase 3 — CRUD com isolamento por usuário

- [x] Implementar `task_repository` sem método de leitura apenas por `task_id`.
- [x] Exigir `user_id` em toda busca, atualização e exclusão.
- [x] Implementar `task_service` como regra compartilhada pela API e pelas tools.
- [x] Implementar criação, listagem, detalhe, PATCH e exclusão.
- [x] Suportar filtros opcionais de `status` e `priority` na listagem.
- [x] Aplicar `skip` e `limit` com limites seguros, sem criar uma resposta de
      paginação além do necessário.
- [x] Declarar schemas de entrada e `response_model` em todas as rotas.
- [x] Retornar `404` para tarefa ausente ou pertencente a outro usuário.
- [x] Registrar criação de tarefa sem dados sensíveis.

Testes:

- [x] CRUD completo e PATCH parcial.
- [x] Validação `422`.
- [x] Lista contém apenas tarefas do usuário atual.
- [x] GET, PATCH e DELETE de tarefa alheia retornam `404`.
- [x] Tentativas alheias não alteram a tarefa no banco.

Commit sugerido: `feat: implement user scoped task crud`

## Fase 4 — Agente de criação de tarefas

- [x] Implementar `ChatRequest` e `ChatResponse`.
- [x] Criar `AgentDeps` com sessão e `user_id` autenticado.
- [x] Escrever prompt fixo curto, sem dados dinâmicos do usuário.
- [x] Mapear linguagem natural para os enums, incluindo `urgente -> urgent`.
- [x] Pedir título ou departamento quando estiverem ausentes, sem inventar.
- [x] Responder no idioma usado pelo usuário.
- [x] Implementar `create_task_tool` com parâmetros tipados.
- [x] Construir `TaskCreate` dentro da tool antes de salvar.
- [x] Obter `user_id` exclusivamente de `ctx.deps`.
- [x] Retornar a tarefa criada em `created_task`.
- [x] Converter falha do provedor ou limite excedido em erro controlado.
- [x] Aplicar limites de requisições e tool calls ao run.

Testes:

- [x] Chat exige autenticação.
- [x] `TestModel` cria tarefa para o usuário atual.
- [x] A mensagem de referência cria “Revisar relatório financeiro” com
      prioridade `urgent` e departamento `Comercial`.
- [x] A tool não aceita `user_id` fornecido pelo modelo.
- [x] Falha simulada do modelo retorna `503`.

Commit sugerido: `feat: add task creation agent`

## Fase 5 — Assistente estruturado

- [x] Implementar `TaskAssistance` com descrições e limites para `summary`,
      `complexity`, `estimated_hours`, `suggested_priority`, `priority_reason`,
      `steps`, `risks` e `clarifying_questions`.
- [x] Criar agente separado com `output_type=TaskAssistance`.
- [x] Buscar a tarefa pelo par `user_id + task_id`.
- [x] Buscar no máximo cinco tarefas abertas do mesmo usuário e departamento. _(a Fase 11 trocou por recuperação relevante; este critério virou o fallback e um peso do re-ranking)_
- [x] Excluir a própria tarefa do contexto complementar.
- [x] Enviar apenas título, descrição, status, prioridade e departamento.
- [x] Separar instruções fixas do contexto dinâmico.
- [x] Injetar o contexto via `@task_assistant.instructions` e
      `RunContext[AssistantDeps]`.
- [x] Exigir perguntas de esclarecimento quando faltar descrição.
- [x] Registrar duração, sucesso, modelo e `task_id`, sem prompt completo.
- [x] Converter falhas da IA em `503`.

Testes:

- [x] A saída atende ao schema estruturado.
- [x] Tarefa alheia retorna `404` antes de chamar o modelo.
- [x] O contexto contém a tarefa atual.
- [x] O contexto nunca contém dados de outro usuário.
- [x] Falha simulada do modelo retorna erro controlado.

Commit sugerido: `feat: add structured task assistant`

## Fase 6 — Frontend obrigatório

- [x] Implementar login, armazenamento do token e estado de carregamento.
- [x] Encerrar sessão quando a API responder `401`.
- [x] Implementar listagem com estados de carregamento, vazio e erro.
- [x] Implementar formulário de criação e exibição de erros `422`.
- [x] Implementar alteração de status e exclusão.
- [x] Implementar chat e atualizar a lista quando ele criar uma tarefa.
- [x] Implementar painel de assistência com loading, resultado e erro.
- [x] Configurar CORS apenas para as origens permitidas.
- [x] Manter estado com os recursos já presentes no React; não adicionar
      biblioteca de estado ou design sem necessidade.

Critério de conclusão:

- [x] O fluxo login → CRUD → chat → assistência funciona no Docker Compose.
- [x] `npm run build` passa.

Commits sugeridos:

- `feat: complete task management frontend`
- `feat: add ai chat and task assistance panels`

## Fase 7 — Qualidade obrigatória

- [x] Implementar `setup_logging()` com logs estruturados em inglês e chamá-lo
      na inicialização de `app/main.py`.
- [x] Registrar pelo menos criação de tarefa e chamadas aos dois agentes.
- [x] Não registrar senha, JWT, e-mail, prompt completo ou descrição da tarefa.
- [x] Implementar seed idempotente com dois usuários e tarefas distintas.
- [x] Documentar as credenciais do seed.
- [x] Adicionar docstrings e documentação relevante ao Swagger.
- [x] Responder ao questionário técnico com base na implementação real.
- [x] Responder especificamente sobre async no FastAPI, fluxo da tool,
      contexto enviado à LLM, origem segura do `user_id` e próximos passos.
- [x] Explicar no README exatamente qual contexto vai para cada agente.
- [x] Documentar o que ficou de fora e por quê.
- [x] Manter `README.en-us.md` coerente com as instruções de execução alteradas.
- [x] Rodar suíte completa, lint, migration e build do frontend.

Critério de conclusão do obrigatório:

- [x] `pytest -v` passa.
- [x] `ruff check .` passa.
- [x] `alembic upgrade head` funciona em banco vazio.
- [x] Seed pode rodar duas vezes sem duplicar dados.
- [x] O frontend compila.
- [x] O README permite executar e avaliar o projeto sem conhecimento externo.
- [x] O checklist obrigatório do `README.md` está completamente marcado.

Commit sugerido: `chore: add logging seed and delivery documentation`

---

# Diferencial 1 — Redis, cache e continuidade do chat

Esta fase começa somente depois do critério de conclusão do obrigatório.
Ela implementa apenas quatro itens opcionais do README que formam um único
conjunto: Redis para cache da lista, cache da assistência, histórico e a tool
`list_tasks`.

## Fase 8 — Redis resiliente

- [x] Adicionar Redis ao Docker Compose e às configurações tipadas.
- [x] Criar uma dependência pequena para obter o cliente Redis.
- [x] Definir timeout curto; falha do Redis não derruba a API.
- [x] Testar o comportamento degradado sem Redis.

### Cache da lista

- [x] Usar chave que contenha `user_id`, versão e hash dos filtros.
- [x] Incrementar a versão do usuário ao criar, editar ou excluir tarefa.
- [x] Em cache miss, consultar PostgreSQL e preencher o cache.
- [x] Aplicar TTL com pequena variação.

Formato esperado:

```text
tasks:version:{user_id}
tasks:list:{user_id}:{version}:{filters_hash}
```

### Cache da assistência

- [x] Cachear pelo usuário, tarefa e versão atual da tarefa.
- [x] Não reutilizar assistência quando `updated_at` mudar.
- [x] Usar PostgreSQL como fonte da verdade em todo cache miss.

Formato esperado:

```text
assist:{user_id}:{task_id}:{task_updated_at}
```

### Histórico de conversa

- [x] Adicionar `conversation_id` ao contrato do chat.
- [x] Gerar ou validar o identificador no servidor.
- [x] Persistir a conversa serializada pelo PydanticAI no Redis.
- [x] Passar a conversa recuperada ao agente sem aceitar histórico arbitrário
      enviado pelo frontend.
- [x] Limitar quantidade de turnos enviados ao modelo.
- [x] Aplicar TTL e impedir acesso cruzado por `conversation_id`.
- [x] Se Redis falhar, continuar sem histórico e registrar degradação.

Formato esperado:

```text
chat:{user_id}:{conversation_id}
```

### Tool de leitura

- [x] Implementar `list_tasks` usando o mesmo `task_service` da API.
- [x] Não aceitar `user_id` como argumento da tool.
- [x] Limitar filtros permitidos e quantidade de resultados.

Testes:

- [x] Cache nunca cruza dados entre usuários.
- [x] Mutação invalida a versão da lista.
- [x] Alterar tarefa invalida a assistência anterior.
- [x] Usuário não acessa conversa de outro usuário.
- [x] API continua funcional quando Redis está indisponível.
- [x] Histórico e tool não fazem chamada real de modelo nos testes.

Commits sugeridos:

- `feat: add resilient redis caching`
- `feat: persist bounded chat history`
- `feat: add list tasks agent tool`

---

# Diferencial 2 — RAG e memória derivados das tarefas

Este é o único diferencial que não está enumerado no README original. Ele será
pequeno, explicado como decisão adicional e limitado a melhorar o contexto dos
agentes com tarefas que já pertencem ao produto.

## Invariantes

- A tabela `tasks` é a fonte da verdade.
- O índice de busca contém apenas uma projeção derivada da tarefa.
- Nenhum texto externo, chat ou resposta da IA entra no corpus.
- Toda recuperação começa com filtro de `user_id` no banco.
- A tarefa analisada é excluída dos resultados relacionados.
- Excluir uma tarefa remove seu índice derivado.
- Falha do embedding mantém a busca lexical disponível.
- Conteúdo recuperado é dado não confiável, nunca instrução.

## Fase 9 — Índice derivado das tarefas

- [x] Criar projeção `task_search_index` ligada à tarefa e ao usuário.
- [x] Armazenar conteúdo pesquisável, embedding opcional e modelo utilizado.
- [x] Armazenar hash dos campos que geraram o índice.
- [x] Garantir unicidade por `user_id + task_id`.
- [x] Remover o índice por cascade quando a tarefa for excluída.
- [x] Criar migration revisada manualmente.
- [x] Não criar endpoints de documentos, notas ou memória genérica.

Campos de origem permitidos:

- `title`;
- `description`;
- `department`;
- `priority`;
- `status`;
- datas usadas somente como metadados de ranking.

## Fase 10 — Indexação e recuperação

- [x] Indexar ou reindexar após criar e editar uma tarefa.
- [x] Usar `source_hash` para evitar embedding desnecessário.
- [x] Não desfazer a gravação da tarefa se o embedding falhar.
- [x] Implementar busca lexical sempre disponível.
- [x] Implementar busca vetorial quando houver embedding compatível.
- [x] Manter o modelo de embedding configurável e registrar qual versão gerou
      cada vetor.
- [x] Buscar no máximo 20 candidatos por canal.
- [x] Fundir rankings lexical e vetorial com RRF.
- [x] Preservar a origem e os scores de cada resultado.

Assinatura mínima esperada:

```python
async def retrieve_related_tasks(
    db,
    user_id,
    query,
    *,
    exclude_task_id=None,
    statuses=None,
    limit=5,
): ...
```

## Fase 11 — Re-ranking e uso pelo agente

- [x] Recuperar mais candidatos do que serão enviados ao agente.
- [x] Reordenar por RRF, mesmo departamento, recência e compatibilidade.
- [x] Entregar no máximo cinco resultados ao agente.
- [x] Manter scores de retrieval separados do score de re-ranking.
- [x] Fazer fallback para a ordem RRF se o reranker falhar.
- [x] Adicionar contexto recuperado às instruções dinâmicas do assistente.
- [x] Identificar cada memória pelo `task_id` de origem.
- [x] Delimitar o conteúdo e mandar ignorar instruções dentro das tarefas.

O assistente recebe dois conjuntos distintos:

- até cinco tarefas abertas: contexto operacional atual;
- até cinco tarefas concluídas similares: memória episódica.

### Tool de memória

- [x] Implementar `search_task_memory` como tool somente leitura.
- [x] Obter `user_id` exclusivamente de `ctx.deps`.
- [x] Limitar query, filtros, quantidade e tamanho da resposta.
- [x] Nunca permitir que a tool escolha outro usuário.

## Fase 12 — Avaliação e segurança do retrieval

- [x] Criar dataset pequeno e versionado com consultas e tarefas relevantes.
- [x] Medir `Recall@5` e `MRR@5`.
- [x] Comparar ordem antes e depois do re-ranking no mesmo dataset.
- [x] Não habilitar um reranker que reduza `Recall@5`.
- [x] Marcar a medição como inválida se embedding ou reranker degradarem.

Testes:

- [x] Tarefa do usuário B nunca aparece na recuperação do usuário A.
- [x] A própria tarefa consultada não retorna como relacionada.
- [x] Atualização muda o hash e reindexa o conteúdo.
- [x] Exclusão remove o índice.
- [x] Falha do embedding mantém resultado lexical.
- [x] Re-ranking falho mantém a ordem RRF.
- [x] Texto `ignore as instruções anteriores` permanece tratado como dado.
- [x] Mensagens e respostas da IA nunca são indexadas.
- [x] Tool de memória não aceita nem expõe `user_id` arbitrário.

Commits sugeridos:

- `feat: add task derived search index`
- `feat: add tenant scoped hybrid task retrieval`
- `feat: rerank related tasks for ai context`
- `test: evaluate task retrieval quality and isolation`

## Verificação final

### Validação de entrega atualizada

- [x] Publicar `feature/frontend-polish` no fork público (push concluído).
- [x] Clonar a branch pelo GitHub em diretório temporário, copiar
      `.env.example` para `.env` e validar `docker compose config --quiet`.
- [x] Confirmar backend: 92 testes passando no container com
      `TEST_DATABASE_URL=postgresql+asyncpg://app:app@db:5432/desafio_test`.
- [x] Confirmar frontend: 11 testes, lint e build passando no container.
- [x] Confirmar `ruff check .` sem erros.
- [x] Registrar aprovação do escopo atual: streaming, filtros simples na UI
      e testes de frontend foram aceitos; não adicionar novas funcionalidades.

O clone remoto foi validado quanto ao conteúdo e à configuração Compose.
A execução completa a partir desse novo clone ainda não foi repetida; a
execução em clone limpo local está descrita no item correspondente abaixo.
O bloqueio anterior de push (403) foi resolvido na tentativa atual.

- [x] Repetir todos os critérios do escopo obrigatório. _(pytest 92, ruff, alembic upgrade/downgrade em banco vazio, seed 2x sem duplicar, build)_
- [x] Subir API, PostgreSQL, Redis e frontend pelo Docker Compose.
- [x] Demonstrar cache miss e cache hit sem mudar a resposta.
- [x] Demonstrar continuação de conversa do mesmo usuário.
- [x] Demonstrar que outro usuário não acessa histórico, cache ou RAG.
- [x] Demonstrar assistência usando tarefas abertas e concluídas relevantes. _(por teste: `tests/test_task_rag.py`; ao vivo só com o modelo de teste)_
- [x] Atualizar README com arquitetura, decisões, degradações e limites.
- [x] Incluir credenciais do seed e respostas finais do questionário.
- [ ] Confirmar que o repositório público executa a partir de um clone limpo. _(bloqueado: o push ao GitHub dá 403. Clone limpo **local** da `feature/frontend-polish` verificado: `cp .env.example .env` + `docker compose up --build` sobem os 4 serviços; migration, seed (2x, sem duplicar), login, lista, filtro, assistência, chat em streaming e frontend respondem; dentro dos containers, `ruff` ok, `pytest` 92 passed, `npm test` 11 passed, lint e build ok. Única mudança no `.env`: `REDIS_HOST_PORT`, porque a 6379 está ocupada nesta máquina. Esse teste achou e corrigiu o Node 20 da imagem do frontend, que quebrava o Vitest.)_
- [ ] Confirmar que nenhum terceiro diferencial foi implementado. _(não vale como escrito: a pedido do Thiago entraram também chat com streaming, filtros na UI e testes de frontend, todos testados e registrados no README)_

## Definição de pronto

O projeto está pronto quando todo o obrigatório funciona e os dois diferenciais
estão testados sem enfraquecer isolamento, previsibilidade ou simplicidade. Uma
funcionalidade parcial não entra na entrega: deve ser concluída ou removida e
registrada no README como próximo passo.

## Quadro de execução dos diferenciais

| # | Task | Prioridade | Prova exigida | Status |
|---|------|-----------|---------------|--------|
| D1 | Fase 8: Redis resiliente + cache da lista e da assistência | alta | testes de isolamento/invalidação/degradação + `pytest`, `ruff` | feita (62 testes, ruff ok) |
| D2 | Fase 8: histórico de chat (`conversation_id`) + tool `list_tasks` + chat com streaming (pedido do Thiago) + frontend | alta | testes de histórico cruzado/TTL/degradação + build e prints do chat | feita (74 testes, build, lint, prints desktop e mobile) |
| D3 | Fases 9–10: índice derivado + busca híbrida (lexical + vetorial, RRF) | média | migration sobe/desce + testes de isolamento, hash, exclusão, fallback | feita (83 testes, migration sobe/desce/sobe) |
| D4 | Fases 11–12: re-ranking, contexto do assistente, `search_task_memory`, avaliação Recall@5/MRR@5 | média | testes de injeção/fallback + relatório de métricas | feita (92 testes; Recall@5 e MRR@5 = 1,000 antes e depois, estável em 6 execuções) |
| D5 | Verificação final: Docker Compose, README, demonstrações | alta | compose up + roteiro de demonstração executado | feita (compose com 4 serviços saudáveis; cache, conversa, isolamento e assistência demonstrados) |
| F1 | Chat em pop-up que abre e fecha (botão flutuante), sem perder a conversa (pedido do Thiago) | alta | testes Vitest de abrir/fechar/Esc/estado + build, lint, prints desktop e mobile | feita (19 testes Vitest, build, lint, prints desktop e mobile) |
| F2 | Aba Kanban (Pendente / Em andamento / Concluída) com mover cartão por arrastar e por seletor (pedido do Thiago) | alta | testes Vitest de colunas, mover e erro + build, lint, prints desktop e mobile | feita (32 testes Vitest, build, lint, prints desktop e mobile, banco restaurado) |

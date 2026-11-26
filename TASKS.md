# Plano de execução

Este arquivo é a fonte de verdade do trabalho do desafio. A ordem abaixo protege
o prazo: primeiro entregamos todo o escopo obrigatório; depois implementamos
somente os dois diferenciais definidos neste plano.

Fonte de requisitos: `README.md`. Em caso de conflito, o obrigatório do README
vence. Os diferenciais não podem atrasar, substituir ou enfraquecer um requisito
obrigatório.

## Contrato de escopo

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
- Qualquer outro item opcional do README.

`user_id` é a fronteira de isolamento. Ele sempre vem do JWT e do contexto da
requisição, nunca de argumentos produzidos pela LLM.

## Regras de execução

- [ ] Trabalhar em branches `feature/...` pequenas.
- [ ] Fazer commits convencionais e focados.
- [ ] Não iniciar os diferenciais antes de todo o obrigatório estar verde.
- [ ] Se um diferencial ficar parcial, removê-lo da entrega em vez de manter um
      fluxo quebrado.
- [ ] Escrever o teste de isolamento junto com cada acesso novo a dados.
- [ ] Não chamar provedores reais nos testes automatizados.
- [ ] Atualizar este arquivo ao concluir ou alterar uma decisão.

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
- [ ] Criar a branch `feature/project-foundation`.
- [ ] Criar `.env` local a partir de `.env.example` sem versionar segredos.
- [ ] Definir `TEST_DATABASE_URL` para um PostgreSQL separado.
- [ ] Configurar fixtures assíncronas e override de `get_db`.
- [ ] Bloquear chamadas reais de modelo durante os testes.
- [ ] Confirmar que frontend e API compilam antes das mudanças.

Critério de conclusão:

- [ ] `test_health.py` passa usando o ambiente de testes documentado.
- [ ] Nenhum teste pode acessar uma LLM real.

Commit sugerido: `test: configure isolated async test database`

## Fase 1 — Domínio de tarefas e banco

- [ ] Implementar `TaskStatus` e `TaskPriority` uma única vez e reutilizá-los.
- [ ] Implementar `TaskCreate`, `TaskUpdate` e `TaskResponse` com
      `from_attributes=True` na resposta.
- [ ] Aplicar limites de tamanho aos campos recebidos pela API e pela IA.
- [ ] Implementar o model `Task` com `Mapped[...]`.
- [ ] Incluir `title`, `description`, `status`, `priority`, `department`,
      `user_id`, `created_at` e `updated_at`.
- [ ] Criar FK obrigatória para `users.id` e índices úteis por usuário.
- [ ] Garantir `created_at` e `updated_at` no banco.
- [ ] Importar `Task` em `app/models/__init__.py`.
- [ ] Criar e revisar a migration de `users` e `tasks`.

Critério de conclusão:

- [ ] Migration sobe e desce em um banco vazio.
- [ ] Payload inválido é rejeitado antes de acessar o repositório.

Commit sugerido: `feat: add task model schemas and migration`

## Fase 2 — Autenticação JWT

- [ ] Implementar `RegisterRequest`, `LoginRequest` ou formulário OAuth2,
      `TokenResponse` e `UserResponse`.
- [ ] Implementar o repositório de usuários.
- [ ] Implementar registro com hash bcrypt e resposta `409` para duplicidade.
- [ ] Implementar login e emissão de JWT.
- [ ] Implementar `get_current_user` com tratamento uniforme de `401`.
- [ ] Rejeitar token inválido, expirado, usuário ausente ou inativo.
- [ ] Implementar `GET /v1/auth/me`.
- [ ] Adicionar summaries e response models às rotas.

Testes:

- [ ] Registro bem-sucedido.
- [ ] E-mail duplicado.
- [ ] Login válido e senha inválida.
- [ ] Token ausente, inválido e usuário inativo.

Commit sugerido: `feat: implement jwt authentication`

## Fase 3 — CRUD com isolamento por usuário

- [ ] Implementar `task_repository` sem método de leitura apenas por `task_id`.
- [ ] Exigir `user_id` em toda busca, atualização e exclusão.
- [ ] Implementar `task_service` como regra compartilhada pela API e pelas tools.
- [ ] Implementar criação, listagem, detalhe, PATCH e exclusão.
- [ ] Suportar filtros opcionais de `status` e `priority` na listagem.
- [ ] Aplicar `skip` e `limit` com limites seguros, sem criar uma resposta de
      paginação além do necessário.
- [ ] Declarar schemas de entrada e `response_model` em todas as rotas.
- [ ] Retornar `404` para tarefa ausente ou pertencente a outro usuário.
- [ ] Registrar criação de tarefa sem dados sensíveis.

Testes:

- [ ] CRUD completo e PATCH parcial.
- [ ] Validação `422`.
- [ ] Lista contém apenas tarefas do usuário atual.
- [ ] GET, PATCH e DELETE de tarefa alheia retornam `404`.
- [ ] Tentativas alheias não alteram a tarefa no banco.

Commit sugerido: `feat: implement user scoped task crud`

## Fase 4 — Agente de criação de tarefas

- [ ] Implementar `ChatRequest` e `ChatResponse`.
- [ ] Criar `AgentDeps` com sessão e `user_id` autenticado.
- [ ] Escrever prompt fixo curto, sem dados dinâmicos do usuário.
- [ ] Mapear linguagem natural para os enums, incluindo `urgente -> urgent`.
- [ ] Pedir título ou departamento quando estiverem ausentes, sem inventar.
- [ ] Responder no idioma usado pelo usuário.
- [ ] Implementar `create_task_tool` com parâmetros tipados.
- [ ] Construir `TaskCreate` dentro da tool antes de salvar.
- [ ] Obter `user_id` exclusivamente de `ctx.deps`.
- [ ] Retornar a tarefa criada em `created_task`.
- [ ] Converter falha do provedor ou limite excedido em erro controlado.
- [ ] Aplicar limites de requisições e tool calls ao run.

Testes:

- [ ] Chat exige autenticação.
- [ ] `TestModel` cria tarefa para o usuário atual.
- [ ] A mensagem de referência cria “Revisar relatório financeiro” com
      prioridade `urgent` e departamento `Comercial`.
- [ ] A tool não aceita `user_id` fornecido pelo modelo.
- [ ] Falha simulada do modelo retorna `503`.

Commit sugerido: `feat: add task creation agent`

## Fase 5 — Assistente estruturado

- [ ] Implementar `TaskAssistance` com descrições e limites para `summary`,
      `complexity`, `estimated_hours`, `suggested_priority`, `priority_reason`,
      `steps`, `risks` e `clarifying_questions`.
- [ ] Criar agente separado com `output_type=TaskAssistance`.
- [ ] Buscar a tarefa pelo par `user_id + task_id`.
- [ ] Buscar no máximo cinco tarefas abertas do mesmo usuário e departamento.
- [ ] Excluir a própria tarefa do contexto complementar.
- [ ] Enviar apenas título, descrição, status, prioridade e departamento.
- [ ] Separar instruções fixas do contexto dinâmico.
- [ ] Injetar o contexto via `@task_assistant.instructions` e
      `RunContext[AssistantDeps]`.
- [ ] Exigir perguntas de esclarecimento quando faltar descrição.
- [ ] Registrar duração, sucesso, modelo e `task_id`, sem prompt completo.
- [ ] Converter falhas da IA em `503`.

Testes:

- [ ] A saída atende ao schema estruturado.
- [ ] Tarefa alheia retorna `404` antes de chamar o modelo.
- [ ] O contexto contém a tarefa atual.
- [ ] O contexto nunca contém dados de outro usuário.
- [ ] Falha simulada do modelo retorna erro controlado.

Commit sugerido: `feat: add structured task assistant`

## Fase 6 — Frontend obrigatório

- [ ] Implementar login, armazenamento do token e estado de carregamento.
- [ ] Encerrar sessão quando a API responder `401`.
- [ ] Implementar listagem com estados de carregamento, vazio e erro.
- [ ] Implementar formulário de criação e exibição de erros `422`.
- [ ] Implementar alteração de status e exclusão.
- [ ] Implementar chat e atualizar a lista quando ele criar uma tarefa.
- [ ] Implementar painel de assistência com loading, resultado e erro.
- [ ] Configurar CORS apenas para as origens permitidas.
- [ ] Manter estado com os recursos já presentes no React; não adicionar
      biblioteca de estado ou design sem necessidade.

Critério de conclusão:

- [ ] O fluxo login → CRUD → chat → assistência funciona no Docker Compose.
- [ ] `npm run build` passa.

Commits sugeridos:

- `feat: complete task management frontend`
- `feat: add ai chat and task assistance panels`

## Fase 7 — Qualidade obrigatória

- [ ] Implementar `setup_logging()` com logs estruturados em inglês e chamá-lo
      na inicialização de `app/main.py`.
- [ ] Registrar pelo menos criação de tarefa e chamadas aos dois agentes.
- [ ] Não registrar senha, JWT, e-mail, prompt completo ou descrição da tarefa.
- [ ] Implementar seed idempotente com dois usuários e tarefas distintas.
- [ ] Documentar as credenciais do seed.
- [ ] Adicionar docstrings e documentação relevante ao Swagger.
- [ ] Responder ao questionário técnico com base na implementação real.
- [ ] Responder especificamente sobre async no FastAPI, fluxo da tool,
      contexto enviado à LLM, origem segura do `user_id` e próximos passos.
- [ ] Explicar no README exatamente qual contexto vai para cada agente.
- [ ] Documentar o que ficou de fora e por quê.
- [ ] Manter `README.en-us.md` coerente com as instruções de execução alteradas.
- [ ] Rodar suíte completa, lint, migration e build do frontend.

Critério de conclusão do obrigatório:

- [ ] `pytest -v` passa.
- [ ] `ruff check .` passa.
- [ ] `alembic upgrade head` funciona em banco vazio.
- [ ] Seed pode rodar duas vezes sem duplicar dados.
- [ ] O frontend compila.
- [ ] O README permite executar e avaliar o projeto sem conhecimento externo.
- [ ] O checklist obrigatório do `README.md` está completamente marcado.

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

- [ ] Criar projeção `task_search_index` ligada à tarefa e ao usuário.
- [ ] Armazenar conteúdo pesquisável, embedding opcional e modelo utilizado.
- [ ] Armazenar hash dos campos que geraram o índice.
- [ ] Garantir unicidade por `user_id + task_id`.
- [ ] Remover o índice por cascade quando a tarefa for excluída.
- [ ] Criar migration revisada manualmente.
- [ ] Não criar endpoints de documentos, notas ou memória genérica.

Campos de origem permitidos:

- `title`;
- `description`;
- `department`;
- `priority`;
- `status`;
- datas usadas somente como metadados de ranking.

## Fase 10 — Indexação e recuperação

- [ ] Indexar ou reindexar após criar e editar uma tarefa.
- [ ] Usar `source_hash` para evitar embedding desnecessário.
- [ ] Não desfazer a gravação da tarefa se o embedding falhar.
- [ ] Implementar busca lexical sempre disponível.
- [ ] Implementar busca vetorial quando houver embedding compatível.
- [ ] Manter o modelo de embedding configurável e registrar qual versão gerou
      cada vetor.
- [ ] Buscar no máximo 20 candidatos por canal.
- [ ] Fundir rankings lexical e vetorial com RRF.
- [ ] Preservar a origem e os scores de cada resultado.

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

- [ ] Recuperar mais candidatos do que serão enviados ao agente.
- [ ] Reordenar por RRF, mesmo departamento, recência e compatibilidade.
- [ ] Entregar no máximo cinco resultados ao agente.
- [ ] Manter scores de retrieval separados do score de re-ranking.
- [ ] Fazer fallback para a ordem RRF se o reranker falhar.
- [ ] Adicionar contexto recuperado às instruções dinâmicas do assistente.
- [ ] Identificar cada memória pelo `task_id` de origem.
- [ ] Delimitar o conteúdo e mandar ignorar instruções dentro das tarefas.

O assistente recebe dois conjuntos distintos:

- até cinco tarefas abertas: contexto operacional atual;
- até cinco tarefas concluídas similares: memória episódica.

### Tool de memória

- [ ] Implementar `search_task_memory` como tool somente leitura.
- [ ] Obter `user_id` exclusivamente de `ctx.deps`.
- [ ] Limitar query, filtros, quantidade e tamanho da resposta.
- [ ] Nunca permitir que a tool escolha outro usuário.

## Fase 12 — Avaliação e segurança do retrieval

- [ ] Criar dataset pequeno e versionado com consultas e tarefas relevantes.
- [ ] Medir `Recall@5` e `MRR@5`.
- [ ] Comparar ordem antes e depois do re-ranking no mesmo dataset.
- [ ] Não habilitar um reranker que reduza `Recall@5`.
- [ ] Marcar a medição como inválida se embedding ou reranker degradarem.

Testes:

- [ ] Tarefa do usuário B nunca aparece na recuperação do usuário A.
- [ ] A própria tarefa consultada não retorna como relacionada.
- [ ] Atualização muda o hash e reindexa o conteúdo.
- [ ] Exclusão remove o índice.
- [ ] Falha do embedding mantém resultado lexical.
- [ ] Re-ranking falho mantém a ordem RRF.
- [ ] Texto `ignore as instruções anteriores` permanece tratado como dado.
- [ ] Mensagens e respostas da IA nunca são indexadas.
- [ ] Tool de memória não aceita nem expõe `user_id` arbitrário.

Commits sugeridos:

- `feat: add task derived search index`
- `feat: add tenant scoped hybrid task retrieval`
- `feat: rerank related tasks for ai context`
- `test: evaluate task retrieval quality and isolation`

## Verificação final

- [ ] Repetir todos os critérios do escopo obrigatório.
- [ ] Subir API, PostgreSQL, Redis e frontend pelo Docker Compose.
- [ ] Demonstrar cache miss e cache hit sem mudar a resposta.
- [ ] Demonstrar continuação de conversa do mesmo usuário.
- [ ] Demonstrar que outro usuário não acessa histórico, cache ou RAG.
- [ ] Demonstrar assistência usando tarefas abertas e concluídas relevantes.
- [ ] Atualizar README com arquitetura, decisões, degradações e limites.
- [ ] Incluir credenciais do seed e respostas finais do questionário.
- [ ] Confirmar que o repositório público executa a partir de um clone limpo.
- [ ] Confirmar que nenhum terceiro diferencial foi implementado.

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
| D3 | Fases 9–10: índice derivado + busca híbrida (lexical + vetorial, RRF) | média | migration sobe/desce + testes de isolamento, hash, exclusão, fallback | pendente |
| D4 | Fases 11–12: re-ranking, contexto do assistente, `search_task_memory`, avaliação Recall@5/MRR@5 | média | testes de injeção/fallback + relatório de métricas | pendente |
| D5 | Verificação final: Docker Compose, README, demonstrações | alta | compose up + roteiro de demonstração executado | pendente |

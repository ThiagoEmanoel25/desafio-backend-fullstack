# Deploy de demonstração: Vercel e Render

Configuração preparada; a criação dos serviços depende das contas de hospedagem
e da escolha dos planos. Este documento não significa que o deploy já foi feito.

## Topologia

```mermaid
flowchart LR
    Browser[Navegador] --> Vercel[Frontend Vite na Vercel]
    Browser -->|HTTPS, JWT e SSE| Render[FastAPI no Render]
    Render --> Postgres[(PostgreSQL gerenciado)]
    Render --> Redis[(Redis compatível)]
    Render --> OpenAI[API OpenAI]
```

O frontend chama o Render diretamente. O streaming não passa por uma função
serverless da Vercel. Banco e Redis ficam acessíveis ao backend; as credenciais
nunca entram no bundle JavaScript.

## 1. Banco e cache

No Render, crie PostgreSQL na mesma região da API. Escolha o plano no painel
após conferir limites, custo e retenção. Anote a URL interna para a aplicação.

Para manter cache e histórico, crie um serviço compatível com Redis com acesso
da API e use sua URL. Sem Redis, configure `REDIS_URL` como string vazia: CRUD e
IA continuam funcionando, mas sem histórico nem cache. Não use `redis://redis`
no Render: esse hostname existe apenas no Docker Compose local.

## 2. Backend no Render

Crie um Web Service a partir do fork público, branch de entrega:

| Campo | Valor |
|---|---|
| Repositório | `ThiagoEmanoel25/desafio-backend-fullstack` |
| Runtime | Docker |
| Root directory | Raiz do repositório |
| Dockerfile path | `Dockerfile.render` |
| Health check | `/health` |
| Quantidade de instâncias inicial | Uma |

O Dockerfile instala dependências de runtime, aplica migrations e inicia
`uvicorn` sem reload na variável `PORT`. O Compose de desenvolvimento não é
usado neste deploy. Se a migration falhar, a aplicação não inicia.
Para múltiplas instâncias, mova migrations para uma etapa única de release.

Configure estas variáveis no painel do backend:

```dotenv
APP_ENV=production
DEBUG=false
LOG_LEVEL=INFO
DATABASE_URL=postgresql+asyncpg://USUARIO:SENHA@HOST:5432/BANCO
JWT_SECRET_KEY=SEGREDO_ALEATORIO_FORTE
CORS_ORIGINS=https://SEU-FRONTEND.vercel.app
REDIS_URL=URL_INTERNA_DO_REDIS_OU_VAZIO
LLM_MODEL=openai:IDENTIFICADOR_DO_MODELO_DISPONIVEL_NA_SUA_CONTA
OPENAI_API_KEY=CHAVE_DO_PROJETO_OPENAI
EMBEDDING_MODEL=
AI_USER_DAILY_LIMIT=10
AI_GLOBAL_DAILY_LIMIT=50
AI_MAX_OUTPUT_TOKENS=800
PYDANTIC_AI_NO_BANNER=1
```

Use os valores reais, sem os placeholders. Para o driver assíncrono, troque
somente o prefixo `postgresql://` da URL interna por `postgresql+asyncpg://`.
Não copie uma URL com parâmetros específicos de outro driver sem conferir
compatibilidade. Não envie credenciais para arquivos versionados.

Gere o segredo JWT localmente com `openssl rand -hex 32` e cadastre o resultado
apenas no painel. A chave OpenAI deve pertencer a um projeto com faturamento e
acesso ao modelo escolhido. Comece com embeddings desativados para validar o
chat real; ativá-los é uma segunda mudança, com custo e reindexação próprios.

## 3. Frontend na Vercel

Importe o mesmo repositório:

| Campo | Valor |
|---|---|
| Root directory | `frontend` |
| Framework | Vite |
| Node.js | 24.x |
| Install command | `npm ci` |
| Build command | `npm run build` |
| Output directory | `dist` |
| Variável | `VITE_API_URL=https://SUA-API.onrender.com` |

Não inclua `/v1` ou barra final em `VITE_API_URL`. Não coloque a chave OpenAI,
credenciais do banco nem segredo JWT em variáveis `VITE_*`: elas são públicas.
O endereço da API é incorporado durante o build; uma alteração exige redeploy.

Quando a Vercel gerar a URL definitiva, configure essa origem exata em
`CORS_ORIGINS` no Render. URLs de preview diferentes não são autorizadas
automaticamente. CORS não substitui autenticação nem controle de consumo.

## 4. Contas de demonstração e acesso público à IA

O seed de desenvolvimento usa senhas publicadas no README. Não execute esse
seed numa API pública com uma chave paga sem aceitar o risco de consumo por
qualquer pessoa com essas credenciais. Para uma avaliação restrita, crie uma
conta com senha própria pelo cadastro e compartilhe o acesso em privado.

Com `APP_ENV=production`, as quotas são obrigatórias: 10 operações de IA por
usuário e 50 globais por dia UTC (configuráveis acima). O contador fica na tabela
`ai_daily_usage` do PostgreSQL e sobrevive à perda do cache ou reinício da API.
Cada reserva é atômica, incluindo o total global e o do usuário. Criar novas
contas não contorna a quota global. Uma falha ou cancelamento mantém a reserva,
pois o provedor pode já ter cobrado pela execução.

Chat JSON, chat SSE e assistência sem cache reservam uma operação antes de
chamar o modelo. Embeddings, caso habilitados, também reservam operações; se
não houver quota para eles, o sistema mantém a busca lexical. Hits no cache
de assistência não consomem quota. Um run do chat pode fazer até cinco pedidos
ao modelo; a assistência, até três. Cada resposta do modelo tem limite
configurado de 800 tokens de saída. Isso é limite de operações, não de dólares.
Entrada, modelo e preço do provedor também influenciam o custo.

Quota esgotada retorna `429` e `Retry-After` antes de iniciar SSE. Se a verificação
no banco falhar, novas chamadas de IA retornam `503`; não há fallback que permita
chamar o provedor sem contabilização. O CRUD permanece sem essa quota.
Não há rate limiting de login ou cadastro nesta implementação.

Para testar localmente, use `AI_LIMITS_ENABLED=true`. Fora de produção ele fica
desabilitado por padrão para não limitar os testes e a demonstração offline.

O plano gratuito não oferece shell remoto. Para provisionar administrador,
execute `python -m seed.create_admin` localmente com a URL externa do banco de
deploy em `DATABASE_URL` (driver asyncpg e acesso seguro conforme o painel).
Mantenha essa URL fora do Git e restaure o ambiente local ao terminar. Não
exponha um endpoint público de promoção a administrador.

## Limites do Render gratuito

- A API dorme após 15 minutos sem tráfego e pode levar cerca de um minuto para
  acordar. A primeira requisição pode falhar enquanto o serviço inicia.
- O PostgreSQL gratuito expira 30 dias após a criação; planeje exportar os dados
  ou migrar antes disso. Não trate a instância como armazenamento permanente.
- Key Value gratuito não oferece a persistência em disco dos planos pagos;
  cache e histórico podem desaparecer. As quotas usam PostgreSQL por esse motivo.
- A API gratuita possui uma instância; as migrations são feitas na inicialização,
  sem depender de shell remoto ou comandos pre-deploy pagos.
- A infraestrutura gratuita não torna a API da OpenAI gratuita.

## 5. Validação depois do deploy

1. Abrir `https://SUA-API.onrender.com/health` e `/docs`.
2. Abrir a Vercel e registrar uma conta de teste com senha própria.
3. Criar, editar e excluir uma tarefa pelo frontend.
4. Criar uma segunda conta e confirmar que não vê tarefas da primeira.
5. Pedir no chat uma tarefa urgente para o Comercial e conferir os campos.
6. Pedir ajuda sobre uma tarefa sem descrição e conferir perguntas na resposta.
7. Confirmar eventos SSE do chat e que a resposta final atualiza a lista.
8. Se Redis estiver ativo, continuar a conversa e verificar o histórico.
9. Conferir logs sem registrar tokens, senhas ou prompts completos.

Se aparecer `503`, confira o tipo de erro no log: acesso ao modelo, chave,
faturamento e limite do provedor são causas diferentes. Não exponha a exceção
bruta na resposta ao navegador.

## Referências

- [Render: Docker](https://render.com/docs/docker)
- [Render: FastAPI](https://render.com/docs/deploy-fastapi)
- [Render: limites gratuitos](https://render.com/docs/free)
- [Render: Key Value](https://render.com/docs/key-value)
- [Vercel: Vite](https://vercel.com/docs/frameworks/frontend/vite)

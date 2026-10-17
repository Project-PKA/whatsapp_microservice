# Secrets e variáveis do WhatsApp Microservice

> Só **nomes** e onde configurar. Nenhum valor entra neste arquivo. Os valores
> ficam no GitHub e, para guardar localmente enquanto você os junta, em
> `.env.secrets.local` (ignorado pelo git).
>
> O detalhamento completo dos valores compartilhados com o Backend está em
> `Backend/docs/secrets.md`. Aqui ficam só os que este serviço consome.
> Nomes marcados *(proposto)* ainda não existem no código.

## 1. CI e automação (agora)

| Nome | Tipo | Escopo | Para quê | Como obter |
| --- | --- | --- | --- | --- |
| `SONAR_TOKEN` | secret | org ou repo | Análise no CI (`code-quality.yml`) | SonarCloud |
| `GH_PROJECT_TOKEN` | secret | org ou repo | Agente do GitHub mexer no Project | PAT fine-grained com acesso a Projects |
| `PROJECT_URL` | variable | org | GitHub Project | URL do Project |

## 2. Aplicação, por Environment (`dev`, `homolog`, `prod`)

| Nome | Tipo | Para quê | Observação |
| --- | --- | --- | --- |
| `DATABASE_URL` | secret | Conexão com o Postgres usando a **role própria do bot** | Montada com `BOT_DB_PASSWORD`; **não** reutilize o usuário do Backend |
| `BOT_DB_PASSWORD` *(proposto)* | secret | Senha da role do bot | O mesmo valor que o Backend usa ao criar a role |
| `WHATSAPP_SESSION_ENCRYPTION_KEY` *(proposto)* | secret | Descriptografa `whatsapp_sessions.session_data` | **Idêntica à do Backend** |
| `REDIS_URL` *(proposto)* | secret | Fila de abertura e fechamento de leilão, se usar BullMQ | Mesmo Redis do Backend, se compartilharem |

## 3. Deploy na VPS (depois da VPS existir)

O deploy do bot reaproveita o fluxo do Backend (imagem no GHCR, SSH,
`docker compose`). Os mesmos `SSH_HOST`, `SSH_USER`, `SSH_PRIVATE_KEY`,
`SSH_KNOWN_HOSTS` e `GHCR_PULL_TOKEN` descritos em `Backend/docs/secrets.md`
precisam existir também neste repositório. O template menciona
`REGISTRY_TOKEN` em `deploy.yml`; só será necessário se a decisão final usar
outro registry que o GHCR.

## 4. Atenção

- Cada sessão de WhatsApp **é uma credencial**. Nada dela entra em log, em
  issue ou em arquivo versionado.
- Perder `WHATSAPP_SESSION_ENCRYPTION_KEY` invalida todas as sessões salvas.

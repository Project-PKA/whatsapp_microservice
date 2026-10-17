# Deploy

A fundação separa **como publicar**, que depende da plataforma, de **quando,
o quê e com que autorização publicar**, que não depende.

| Camada | Arquivo | Depende da plataforma? |
| --- | --- | --- |
| Gatilhos, ambientes, build único da imagem, smoke test | `.github/workflows/deploy.yml` | Não |
| Política de aprovação e secrets | GitHub Environments (interface) | Não |
| Implantação da imagem | `scripts/deploy.sh` | **Sim** |

Trocar de plataforma é reescrever **um** arquivo: `scripts/deploy.sh`.

---

## Build once, deploy many

```mermaid
graph LR
  M[push em main] --> B["build único:<br/>ghcr.io/org/repo:SHA"]
  B --> D[dev]
  B -. mesma imagem .-> T[test]
  B -. mesma imagem .-> H["homolog<br/>(aprovação)"]
  B -. mesma imagem .-> P["prod<br/>(release + aprovação)"]
```

- A imagem é construída **uma vez**, no push em `main`, com tag = SHA do commit.
- Promover é implantar **a mesma imagem** em outro ambiente. O workflow
  recusa promover um SHA que não tenha imagem, então não existe "build de
  produção" diferente do que foi testado.
- O que muda entre ambientes chega em **runtime**, pelas variables e secrets
  do Environment. Nada de configuração gravada na imagem.
- **Rollback** é reimplantar o SHA anterior: **Actions → Deploy → Run
  workflow**, com o ambiente e o SHA. Não precisa reverter merge.

## Registry da imagem

A variable `IMAGE_REPOSITORY` (do repositório ou da organização, **sem a
tag**) escolhe onde a imagem mora. Sem ela, é o GHCR. O `deploy.yml` detecta
o tipo e faz o login certo, tanto no build quanto na verificação do deploy.

| `IMAGE_REPOSITORY` | Registry | Login | Quando usar |
| --- | --- | --- | --- |
| (vazio) | `ghcr.io/<org>/<repo>` | Automático (`GITHUB_TOKEN`) | Kubernetes, VPS, Azure; ECS com credencial de pull |
| `<conta>.dkr.ecr.<região>.amazonaws.com/<nome>` | AWS ECR | OIDC: secret `AWS_ECR_ROLE_ARN` | AWS: **obrigatório para Lambda**, recomendado para ECS e App Runner |
| Outro (`docker.io/...`, `<região>-docker.pkg.dev/...`) | Docker Hub, Artifact Registry... | Variable `REGISTRY_USERNAME` + secret `REGISTRY_PASSWORD` | Padrão da organização, Cloud Run |

**Role do ECR (`AWS_ECR_ROLE_ARN`):** precisa de push/pull no repositório do
ECR. A trust policy aceita o job de build (sem Environment) **e** os jobs
de deploy (que verificam a imagem):

```json
"StringLike": {
  "token.actions.githubusercontent.com:sub": [
    "repo:SUA-ORG/SEU-REPOSITORIO:ref:refs/heads/main",
    "repo:SUA-ORG/SEU-REPOSITORIO:environment:*"
  ]
}
```

---

## Modelo de ambientes

| Ambiente | Gatilho | Aprovação |
| --- | --- | --- |
| `dev` | Automático a cada push em `main` | Não |
| `test` | Manual (Actions → Deploy → Run workflow) | Não |
| `homolog` | Manual | **Sim** (required reviewers) |
| `prod` | Release publicada pelo release-please, ou manual | **Sim** (required reviewers) |

A aprovação é *protection rule* do Environment, não `if:` no YAML.
Configuração passo a passo em [`SETUP-GITHUB.md`](SETUP-GITHUB.md), seção B4.

---

## O contrato de `scripts/deploy.sh`

**Entrada:**

| Variável | Origem | Sempre presente |
| --- | --- | --- |
| `DEPLOY_ENV` | Workflow | Sim (`dev`/`test`/`homolog`/`prod`) |
| `IMAGE` | Workflow | Sim (`ghcr.io/org/repo:<sha>`, já publicada) |
| `APP_BASE_URL` | Variable do Environment | Se configurada |
| Demais | Secrets e variables repassados no `deploy.yml` | Conforme a receita |

**Saída:** `0` quando implantou; qualquer outro código falha o deploy.

**Troca de versão sem perder trabalho:** a plataforma envia SIGTERM ao
processo antigo. O serviço para de pegar mensagens novas, termina a que está
em andamento e sai. Configure o tempo de encerramento da plataforma
(`terminationGracePeriodSeconds`, `stopTimeout`) maior que o processamento
mais longo. Mensagem interrompida tem de voltar para a fila, não sumir.

**Migrations:** este serviço não migra schema de outro dono. Se ele tem banco
**próprio**, rode as migrations antes da troca de versão, com a mesma imagem
(mesmo padrão do template de backend).

**Cron:** em Kubernetes, prefira `CronJob`; no Cloud Run, *Jobs* com
Cloud Scheduler; no ECS, *scheduled tasks*. Nos três, a promoção continua
sendo "trocar a imagem pelo SHA".

---

## Receita: Kubernetes

**Environment:** `KUBE_CONFIG` (secret; ou OIDC da nuvem + `get-credentials`),
`KUBE_NAMESPACE` e `KUBE_DEPLOYMENT` (variables).

```sh
# scripts/deploy.sh (trecho a colocar no lugar do bloco PENDING)
: "${KUBE_CONFIG:?}" "${KUBE_NAMESPACE:?}" "${KUBE_DEPLOYMENT:?}"
printf '%s' "$KUBE_CONFIG" > "$RUNNER_TEMP/kubeconfig"
export KUBECONFIG="$RUNNER_TEMP/kubeconfig"

# Troca de versão e espera o rollout (graceful shutdown no pod antigo).
kubectl -n "$KUBE_NAMESPACE" set image "deployment/$KUBE_DEPLOYMENT" app="$IMAGE"
kubectl -n "$KUBE_NAMESPACE" rollout status "deployment/$KUBE_DEPLOYMENT" --timeout=5m
```

Repasse `KUBE_CONFIG`, `KUBE_NAMESPACE` e `KUBE_DEPLOYMENT` no passo
`Publicar` do `deploy.yml`. Readiness e liveness probes apontam para
`/ready` e `/health`.

## Receita: Google Cloud Run

**Credenciais:** descomente o bloco `google-github-actions/auth` no
`deploy.yml` (OIDC). **Environment:** `CLOUD_RUN_SERVICE`, `GCP_REGION`.

> O Cloud Run não puxa imagens do GHCR diretamente. Copie a imagem para o
> Artifact Registry (`gcrane cp`/`docker tag` + `push`) ou use um repositório
> remoto do Artifact Registry apontando para o `ghcr.io`.

```sh
: "${CLOUD_RUN_SERVICE:?}" "${GCP_REGION:?}"
# Serviço HTTP ou consumidor push: `gcloud run deploy`.
# Cron: `gcloud run jobs deploy ... --image "$IMAGE"` + Cloud Scheduler.
gcloud run deploy "$CLOUD_RUN_SERVICE" --image "$IMAGE" --region "$GCP_REGION" --quiet
```

## Receita: AWS ECS (Fargate)

**Credenciais:** bloco `aws-actions/configure-aws-credentials` (OIDC).
**Environment:** `ECS_CLUSTER`, `ECS_SERVICE`, `AWS_REGION`.

Gere uma nova *task definition* com a imagem (por exemplo, com
`aws-actions/amazon-ecs-render-task-definition` no workflow ou `jq` aqui),
e atualize o serviço com `aws ecs update-service` +
`aws ecs wait services-stable`. Ajuste o `stopTimeout` do container ao
processamento mais longo.

## Receita: AWS Lambda (imagem de container)

Lambda com container encaixa no build once, deploy many: a imagem é a mesma,
só muda a função de cada ambiente.

- **Registry:** a Lambda só aceita imagem do **ECR** da mesma região.
  Configure `IMAGE_REPOSITORY` para o ECR (seção "Registry da imagem").
- **Imagem:** precisa implementar a Runtime Interface da Lambda. Use as
  imagens base `public.ecr.aws/lambda/<linguagem>` no `Dockerfile` ou o
  *runtime interface client* da linguagem.
- **Credenciais:** bloco `aws-actions/configure-aws-credentials` no
  `deploy.yml` (OIDC), com o role do ambiente (`lambda:UpdateFunctionCode`
  e `lambda:GetFunction`).
- **Environment:** variable `LAMBDA_FUNCTION` (uma função por ambiente).

```sh
: "${LAMBDA_FUNCTION:?}"
aws lambda update-function-code --function-name "$LAMBDA_FUNCTION" --image-uri "$IMAGE" >/dev/null
aws lambda wait function-updated --function-name "$LAMBDA_FUNCTION"
```

Repasse `LAMBDA_FUNCTION` no passo `Publicar` do `deploy.yml`.

> **Lambda por zip** (sem container) fica fora deste modelo, porque não há
> imagem para promover. Se for indispensável, publique o zip por SHA num
> bucket S3 no push em `main` e promova o mesmo zip entre ambientes
> (adaptando o `deploy.yml`). A recomendação é usar container.

> **Consumidor de fila (SQS):** o *event source mapping* é criado uma vez na
> infraestrutura; o deploy só troca a imagem. A Lambda termina a invocação em
> andamento antes de usar a versão nova.

## Receita: VPS com docker compose (via SSH)

Para projeto pequeno, uma máquina só.

**Environment:** `SSH_PRIVATE_KEY` (secret), `SSH_HOST` e `SSH_USER`.

```sh
: "${SSH_PRIVATE_KEY:?}" "${SSH_HOST:?}" "${SSH_USER:?}"
key="$RUNNER_TEMP/deploy_key"
printf '%s\n' "$SSH_PRIVATE_KEY" > "$key" && chmod 600 "$key"
ssh -i "$key" -o StrictHostKeyChecking=accept-new "$SSH_USER@$SSH_HOST" \
  "IMAGE='$IMAGE' docker compose -f /srv/app/compose.yaml up -d app"
```

No servidor, o `compose.yaml` usa `image: ${IMAGE}` e um `.env` de produção
que **nunca** passa pelo repositório.


---

## Checklist ao implementar o deploy

- [ ] `scripts/deploy.sh` implanta de verdade e falha com código diferente de 0 no erro
- [ ] Graceful shutdown testado: deploy no meio de um processamento não perde a mensagem
- [ ] Nenhum segredo no código nem em log (use secrets do Environment)
- [ ] Credencial de curta duração (OIDC) sempre que a plataforma suportar
- [ ] Os quatro Environments existem, com aprovação em `homolog` e `prod`
- [ ] `APP_BASE_URL` configurada (sem ela o smoke test é pulado em silêncio)
- [ ] Rollback testado ao menos uma vez, antes de precisar dele
- [ ] O caminho de deploy é **único**: nenhuma integração automática da
      plataforma publicando por fora e ignorando a aprovação

---

## Rollback

<!-- Preencha ao implementar o deploy. Quem estiver de plantão às 3h da manhã
     precisa achar isto em 30 segundos. -->

| Ambiente | Como reverter | Quanto tempo leva |
| --- | --- | --- |
| `prod` | Actions → Deploy → Run workflow: `prod` + SHA anterior | <!-- --> |

**Mensagens processadas pela versão com bug:** <!-- reprocessar? como? -->

**Quando reverter em vez de corrigir:** <!-- critério do time -->

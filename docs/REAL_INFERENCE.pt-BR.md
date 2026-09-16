# Teste local com inferência real

O `.env` real do lab mantém `LLM_BACKEND=gateway`, permissão `0600` e somente a credencial de
consumidor copiada do `.env` do gateway. `OPENAI_API_KEY` está vazio para preenchimento opcional.
Credenciais de provedor e do PDP do modo governado continuam no repositório do gateway.
Os serviços Python não carregam `.env` automaticamente: os comandos abaixo exportam o arquivo
apropriado para cada serviço.

Este teste usa evidências fictícias, `agent.orchestration`, risco `high` e classificação `public`.
Os deployments locais do personal-default aceitam dados até `public`; use apenas o exemplo sintético
abaixo. A classificação de evidências reais deve refletir o conteúdo e requer deployments elegíveis.

| Serviço | Endereço |
| --- | --- |
| Governed LLM Gateway | `http://127.0.0.1:8000` |
| Policy Model Router | `http://127.0.0.1:8001` |
| Agno | `http://127.0.0.1:8101` |
| LangGraph / API do lab | `http://127.0.0.1:8003` |
| PostgreSQL do lab | `127.0.0.1:5432` |

O ranking aprovado padrão do gateway cobre somente `rag.answer`. O helper abaixo escolhe
explicitamente o `ranking_policy.yaml` estático já versionado, que contém `agent.orchestration`.
Isso preserva a autenticação, a decisão do PDP e a seleção/retry/fallback governados; não modifica
artefatos nem escolhe provedor/modelo no agente. Os helpers usam os checkouts irmãos existentes
`../governed-llm-gateway` e `../policy-model-router`.

## 1. Preparar dependências e PostgreSQL

O Docker Desktop está instalado, mas o daemon não estava em execução ao preparar este roteiro.
Abra-o e aguarde a indicação de que está pronto:

```bash
open -a Docker
```

Depois, em um terminal:

```bash
cd /Users/brunovicco/Projects/agent-runtime-boundaries-lab
uv sync --frozen --all-groups
docker compose up -d --wait --wait-timeout 60 postgres
```

O teste começa com `OTEL_ENABLED=false`, então não é necessário iniciar Tempo/Grafana/Collector.

## 2. Terminal do Policy Model Router

```bash
cd /Users/brunovicco/Projects/agent-runtime-boundaries-lab
sh scripts/run_live_policy_router.sh
```

Mantenha esse terminal aberto. O helper exporta a política versionada do gateway e a credencial
do PDP como `API_KEYS`, sem imprimir o segredo nem fornecer chaves de provedor ao processo do PDP.

## 3. Terminal do gateway

```bash
cd /Users/brunovicco/Projects/agent-runtime-boundaries-lab
sh scripts/run_live_gateway.sh
```

Mantenha esse terminal aberto e aguarde a inicialização. Ele carrega as credenciais exclusivamente
do `.env` do gateway. As chaves dos seis provedores estão preenchidas no arquivo existente;
isso verifica configuração, não a validade das credenciais junto aos provedores.

## 4. Terminal do especialista Agno

```bash
cd /Users/brunovicco/Projects/agent-runtime-boundaries-lab
set -a
source .env
set +a
uv run --frozen uvicorn agent_runtime_boundaries.entrypoints.specialist:app \
  --host 127.0.0.1 --port 8101
```

## 5. Terminal do orquestrador LangGraph

```bash
cd /Users/brunovicco/Projects/agent-runtime-boundaries-lab
set -a
source .env
set +a
uv run --frozen uvicorn agent_runtime_boundaries.entrypoints.api:app \
  --host 127.0.0.1 --port 8003
```

## 6. Terminal do teste

Primeiro verifique os serviços sem executar inferência:

```bash
curl --fail-with-body -sS http://127.0.0.1:8001/readyz
curl --fail-with-body -sS http://127.0.0.1:8000/readyz
curl --fail-with-body -sS http://127.0.0.1:8101/health
curl --fail-with-body -sS http://127.0.0.1:8003/health
```

Depois envie uma nova execução pelo caminho completo. Esta chamada usa inferência real e pode
consumir saldo do provedor selecionado pelo gateway:

```bash
run_id="$(date +%Y%m%d%H%M%S)"
curl --fail-with-body -sS --max-time 90 http://127.0.0.1:8003/v1/reviews \
  -H 'content-type: application/json' \
  --data-binary @- <<JSON
{
  "conversation_id": "merchant-synthetic-${run_id}",
  "execution_id": "exec:real-${run_id}",
  "delegation_id": "deleg:real-${run_id}",
  "prompt": "Analise o risco deste comerciante ficticio em portugues. Separe fatos, inferencias e incertezas. Nao aprove nem execute transacoes.",
  "payload": {"synthetic": true, "merchant_tier": "growth", "chargeback_ratio": 0.012}
}
JSON
```

O resultado esperado tem `phase: "completed"`, `specialist_reused: false` e uma análise textual.
O caminho é LangGraph → A2A → Agno → Gateway → PDP/provedor → resultado persistido no ledger.
Falhas do modelo/gateway resultam em erro da API, sem resposta de especialista marcada como sucesso.

Para testar reuso, repita somente o `curl` com os mesmos IDs e o mesmo `run_id`, sem executar novamente
a atribuição que gera o timestamp. O resultado esperado tem `specialist_reused: true`, sem nova
delegação ao especialista. Gere outro `run_id` para exigir uma nova inferência.

## Alternativa com CrewAI

Substitua o terminal do Agno por:

```bash
cd /Users/brunovicco/Projects/agent-runtime-boundaries-lab
set -a
source .env
set +a
uv run --frozen uvicorn agent_runtime_boundaries.entrypoints.crewai_specialist:app \
  --host 127.0.0.1 --port 8102
```

Pare o orquestrador com Ctrl+C e reinicie no terminal dele, com a URL ajustada após carregar `.env`:

```bash
cd /Users/brunovicco/Projects/agent-runtime-boundaries-lab
set -a
source .env
set +a
export SPECIALIST_A2A_URL=http://127.0.0.1:8102/a2a
uv run --frozen uvicorn agent_runtime_boundaries.entrypoints.api:app \
  --host 127.0.0.1 --port 8003
```

Verifique `http://127.0.0.1:8102/health` e envie o teste com um novo `run_id`.
O CrewAI executa duas tarefas sequenciais, podendo consumir mais tempo e chamadas de inferência.

## Alternativa sem gateway: OpenAI direto

Esse caminho funciona com Agno ou CrewAI e não precisa dos serviços Gateway/Policy Model Router
nem de um checkout deles. Inicie apenas PostgreSQL, especialista e API do lab. As evidências são
enviadas diretamente à OpenAI, sem política, auditoria, roteamento e retry/fallback do gateway/PDP.
O adaptador usa a Responses API no endpoint oficial, `store=false`, sem estado de conversa no
provedor nem retries automáticos. A [referência oficial](https://developers.openai.com/api/reference/python/resources/responses/methods/create)
documenta os parâmetros dessa API.

No `.env` do lab, preencha sua chave e selecione o backend:

```dotenv
LLM_BACKEND=openai
OPENAI_API_KEY=sua-chave-openai
OPENAI_MODEL=gpt-4.1-mini
OPENAI_MAX_OUTPUT_TOKENS=2000
OPENAI_REQUEST_TIMEOUT_SECONDS=60
```

`OPENAI_MODEL` pode ser outro modelo disponível à sua conta que suporte texto na Responses API.
As variáveis `GOVERNED_LLM_GATEWAY_*` não são necessárias nesse modo. Manter somente a chave
OpenAI, sem `LLM_BACKEND=openai`, mantém o gateway padrão. Falhas nunca trocam o backend.

Prepare dependências e PostgreSQL:

```bash
cd /Users/brunovicco/Projects/agent-runtime-boundaries-lab
uv sync --frozen --all-groups
docker compose up -d --wait --wait-timeout 60 postgres
```

Pare o especialista anterior com Ctrl+C e inicie o Agno em um terminal:

```bash
cd /Users/brunovicco/Projects/agent-runtime-boundaries-lab
set -a
source .env
set +a
uv run --frozen uvicorn agent_runtime_boundaries.entrypoints.specialist:app \
  --host 127.0.0.1 --port 8101
```

Em outro terminal, inicie ou reinicie a API:

```bash
cd /Users/brunovicco/Projects/agent-runtime-boundaries-lab
set -a
source .env
set +a
unset OPENAI_API_KEY GOVERNED_LLM_GATEWAY_API_KEY
export SPECIALIST_A2A_URL=http://127.0.0.1:8101/a2a
uv run --frozen uvicorn agent_runtime_boundaries.entrypoints.api:app \
  --host 127.0.0.1 --port 8003
```

A API orquestradora não precisa de credenciais de modelo. No terminal de teste, confira o backend
do especialista; `/health` deve informar `"llm_backend":"openai"`:

```bash
curl --fail-with-body -sS http://127.0.0.1:8101/health
curl --fail-with-body -sS http://127.0.0.1:8003/health
```

Envie uma nova execução para realizar inferência cobrada na sua conta OpenAI:

```bash
run_id="openai-$(date +%Y%m%d%H%M%S)"
curl --fail-with-body -sS --max-time 90 http://127.0.0.1:8003/v1/reviews \
  -H 'content-type: application/json' \
  --data-binary @- <<JSON
{
  "conversation_id": "merchant-synthetic-${run_id}",
  "execution_id": "exec:real-${run_id}",
  "delegation_id": "deleg:real-${run_id}",
  "prompt": "Analise o risco deste comerciante ficticio em portugues. Separe fatos, inferencias e incertezas. Nao aprove nem execute transacoes.",
  "payload": {"synthetic": true, "merchant_tier": "growth", "chargeback_ratio": 0.012}
}
JSON
```

Espere `phase: "completed"`, `specialist_reused: false` e uma análise textual. Para comprovar reuso,
repita somente o `curl` com o mesmo `run_id`: espere `specialist_reused: true`, sem nova inferência.
IDs concluídos continuam reutilizando o resultado anterior mesmo após trocar backend/modelo;
gere novos IDs para testar uma nova inferência.

Para OpenAI direto com CrewAI, mantenha a mesma configuração, inicie
`agent_runtime_boundaries.entrypoints.crewai_specialist:app` na porta 8102 e reinicie a API com
`SPECIALIST_A2A_URL=http://127.0.0.1:8102/a2a`, conforme a alternativa CrewAI acima.
O `/health` também informa `llm_backend=openai`; o CrewAI faz duas chamadas sequenciais.

Para voltar ao gateway, defina `LLM_BACKEND=gateway`, confira suas variáveis governadas e reinicie
o especialista. Retome os serviços Gateway/PDP necessários ao modo governado.

## Execução real com OTEL e capturas

A execução registrada em **16/09/2026** usou `OTEL_ENABLED=true` nos dois processos do lab,
o backend `gateway` e evidências sintéticas. A inferência concluiu em **6,544756 s**; a repetição
dos mesmos IDs concluiu em **0,084811 s**, com reuso e resumo idêntico. O Tempo recebeu dois spans
com o mesmo trace ID e relação pai/filho confirmada.

As respostas, os tempos e os spans normalizados estão em
[`evidence/otel-live-run.json`](evidence/otel-live-run.json). As capturas dos READMEs apresentam o
relatório das respostas reais e o trace consultado no Grafana. O relatório pode ser aberto seguindo
[`evidence/README.md`](evidence/README.md).

Para reproduzir, mantenha Gateway/PDP disponíveis e inicie a stack de observabilidade:

```bash
cd /Users/brunovicco/Projects/agent-runtime-boundaries-lab
docker compose up -d postgres tempo otel-collector grafana
curl --fail-with-body -sS http://127.0.0.1:3200/ready
```

O Tempo pode levar alguns segundos para ficar pronto. O Collector recebe OTLP/HTTP em 4318,
encaminha os spans ao Tempo, e a fonte Tempo já está provisionada no Grafana em 3000.

No terminal do Agno, carregue `.env` e habilite OTEL depois de carregá-lo. As portas temporárias
8201/8203 permitem preservar os serviços existentes em 8101/8003:

```bash
cd /Users/brunovicco/Projects/agent-runtime-boundaries-lab
set -a
source .env
set +a
export OTEL_ENABLED=true
export LLM_BACKEND=gateway
uv run --frozen uvicorn agent_runtime_boundaries.entrypoints.specialist:app \
  --host 127.0.0.1 --port 8201
```

No terminal da API:

```bash
cd /Users/brunovicco/Projects/agent-runtime-boundaries-lab
set -a
source .env
set +a
unset OPENAI_API_KEY GOVERNED_LLM_GATEWAY_API_KEY
export OTEL_ENABLED=true
export SPECIALIST_A2A_URL=http://127.0.0.1:8201/a2a
uv run --frozen uvicorn agent_runtime_boundaries.entrypoints.api:app \
  --host 127.0.0.1 --port 8203
```

Use o curl sintético da seção de teste com a URL `http://127.0.0.1:8203/v1/reviews` e novos IDs.
Repita apenas o curl, com os mesmos IDs, para comprovar reuso. Aguarde alguns segundos para o
exportador em lote enviar os spans e consulte o Tempo:

```bash
curl --fail-with-body -sS \
  'http://127.0.0.1:3200/api/search?tags=service.name%3Dlanggraph-orchestrator&limit=20'
```

No Grafana, conclua a configuração inicial de autenticação, abra **Explore**, selecione **Tempo**,
cole o `traceID` retornado no editor e clique **Run query**. O trace arquivado desta execução é
`553921e6193daaaa264e37d077dba594`. Enquanto ele estiver no Tempo local, também pode ser consultado
diretamente:

```bash
curl --fail-with-body -sS \
  http://127.0.0.1:3200/api/traces/553921e6193daaaa264e37d077dba594
```

Verifique `specialist.delegate` no processo `langgraph-orchestrator` e `specialist.handle` no
`agno-risk-specialist`, compartilhando o trace ID e com o segundo span filho do primeiro.
Os atributos registram apenas `operation`. A instrumentação cobre a delegação A2A; spans próprios
do gateway/provedor e de todo o workflow não fazem parte deste trace. A repetição concluída evita
uma nova delegação ao especialista.

## Encerrar

Pare os serviços Python com Ctrl+C nos respectivos terminais. Para parar o PostgreSQL preservando
os dados do teste:

```bash
cd /Users/brunovicco/Projects/agent-runtime-boundaries-lab
docker compose stop postgres
```

O `.env`, os checkouts/configurações e a sintaxe dos helpers foram conferidos. A execução real
com OTEL, a exportação ao Tempo e o reuso do ledger foram verificados no registro arquivado acima.

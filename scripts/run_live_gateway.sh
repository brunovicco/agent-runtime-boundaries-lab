#!/bin/sh
# Reviewed static ranking covers agent.orchestration; approved_ranking.json covers rag.answer only.
set -eu

lab_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
gateway_root=$(CDPATH= cd -- "$lab_root/../governed-llm-gateway" && pwd)

set -a
. "$gateway_root/.env"
set +a

cd "$gateway_root"
exec uv run --frozen --package governed-llm-gateway-api governed-llm-gateway \
    --deployment-root "$gateway_root" \
    --model-registry-path config/profiles/personal-default/model_registry.yaml \
    --provider-runtime-path config/profiles/personal-default/provider_runtime.json \
    --client-auth-path config/profiles/personal-default/client_auth.json \
    --operations-access-path config/profiles/personal-default/operations_access.json \
    --policy-router-path config/profiles/personal-default/policy_router.json \
    --ranking-policy-path config/profiles/personal-default/ranking_policy.yaml \
    --default-max-latency-ms 60000 \
    --default-max-cost-usd 0.05 \
    --host 127.0.0.1 --port 8000

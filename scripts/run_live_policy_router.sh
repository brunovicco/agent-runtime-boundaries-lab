#!/bin/sh
# Local integration helper: the PDP receives only its own authentication secret.
set -eu

lab_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
gateway_root=$(CDPATH= cd -- "$lab_root/../governed-llm-gateway" && pwd)
router_root=$(CDPATH= cd -- "$lab_root/../policy-model-router" && pwd)

set -a
. "$gateway_root/.env"
set +a

: "${POLICY_ROUTER_DEMO_API_KEY:?Configure POLICY_ROUTER_DEMO_API_KEY no .env do gateway}"
API_KEYS=$(python3.13 -c 'import json, os; print(json.dumps({"gateway-demo": os.environ["POLICY_ROUTER_DEMO_API_KEY"]}))')
export API_KEYS
export APP_ENV=development
export ROUTING_POLICY_PATH="$gateway_root/config/deployment/governed-compose-routing-policy.yaml"

unset NVIDIA_API_KEY GEMINI_API_KEY OPENAI_API_KEY ANTHROPIC_API_KEY GROQ_API_KEY OPENROUTER_API_KEY
unset GATEWAY_DEMO_API_KEY POLICY_ROUTER_DEMO_API_KEY

cd "$router_root"
exec uv run --frozen uvicorn policy_model_router.entrypoints.http:app \
    --host 127.0.0.1 --port 8001

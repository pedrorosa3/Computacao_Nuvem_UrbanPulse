#!/usr/bin/env bash
# Cria (ou atualiza) os Secrets do Kubernetes a partir do ficheiro .env.
# Uso: ENV_FILE=~/.env bash ~/kubernetesCloud/create-secrets.sh
set -euo pipefail

ENV_FILE="${ENV_FILE:-$HOME/.env}"
NAMESPACE="${NAMESPACE:-urbanpulse}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Ficheiro $ENV_FILE não encontrado. Copia o .env.example para .env e preenche as passwords." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

apply_secret() {
  local name="$1"; shift
  kubectl create secret generic "$name" -n "$NAMESPACE" "$@" \
    --dry-run=client -o yaml | kubectl apply -f -
}

apply_secret location-db-secrets \
  --from-literal=username=admin \
  --from-literal=password="${LOCATION_DB_PASSWORD:?}" \
  --from-literal=dbname=location_db

apply_secret trip-db-secrets \
  --from-literal=username=admin \
  --from-literal=password="${TRIP_DB_PASSWORD:?}" \
  --from-literal=dbname=trip_db

apply_secret demand-db-secrets \
  --from-literal=username=urbanpulse \
  --from-literal=password="${DEMAND_DB_PASSWORD:?}" \
  --from-literal=dbname=demand_db

apply_secret revenue-db-secrets \
  --from-literal=username=urbanpulse \
  --from-literal=password="${REVENUE_DB_PASSWORD:?}" \
  --from-literal=dbname=revenue_db

apply_secret payment-db-secrets \
  --from-literal=username=admin \
  --from-literal=password="${PAYMENT_DB_PASSWORD:?}"

apply_secret grafana-secret \
  --from-literal=admin-user=admin \
  --from-literal=admin-password="${GRAFANA_ADMIN_PASSWORD:?}"

echo "Secrets criados no namespace $NAMESPACE."

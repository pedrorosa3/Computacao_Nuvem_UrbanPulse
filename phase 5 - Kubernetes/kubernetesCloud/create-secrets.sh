#!/usr/bin/env bash
# Cria (ou atualiza) os Secrets das BDs no Kubernetes a partir do ficheiro .env.
# Uso (Cloud Shell): ENV_FILE=~/.env bash ~/kubernetesCloud/create-secrets.sh
# Uso (local):       ENV_FILE=.env bash kubernetesCloud/create-secrets.sh
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

# Cada secret só é criado se a password estiver definida no .env
[[ -n "${LOCATION_DB_PASSWORD:-}" ]] && apply_secret location-db-secrets --from-literal=password="$LOCATION_DB_PASSWORD"
[[ -n "${TRIP_DB_PASSWORD:-}"     ]] && apply_secret trip-db-secrets     --from-literal=password="$TRIP_DB_PASSWORD"
[[ -n "${DEMAND_DB_PASSWORD:-}"   ]] && apply_secret demand-db-secrets   --from-literal=password="$DEMAND_DB_PASSWORD"
[[ -n "${REVENUE_DB_PASSWORD:-}"  ]] && apply_secret revenue-db-secrets  --from-literal=password="$REVENUE_DB_PASSWORD"
[[ -n "${PAYMENT_DB_PASSWORD:-}"  ]] && apply_secret payment-db-secrets  --from-literal=password="$PAYMENT_DB_PASSWORD"

echo "Secrets criados no namespace $NAMESPACE."

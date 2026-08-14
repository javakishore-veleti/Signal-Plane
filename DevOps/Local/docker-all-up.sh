#!/usr/bin/env bash
# Start the local substrate.
#
#   ./docker-all-up.sh                     core stacks: Postgres, Kafka, Redis, MinIO
#   ./docker-all-up.sh all                 core plus Observability
#   ./docker-all-up.sh Kafka Redis         only those
#   ./docker-all-up.sh --no-wait           do not block on health checks
#
# Waiting on health is the default because the alternative is a race: services
# that start against a broker still forming get confusing errors that look like
# configuration problems.

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_common.sh"

WAIT=1
ARGS=()
for a in "$@"; do
  case "$a" in
    --no-wait) WAIT=0 ;;
    --with-observability) ARGS+=("${CORE_STACKS[@]}" Observability) ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) ARGS+=("$a") ;;
  esac
done

require_docker
ensure_network

declare -a STACKS
resolve_stacks STACKS "${ARGS[@]}"

for s in "${STACKS[@]}"; do
  log "starting ${s}"
  if [[ $WAIT -eq 1 ]]; then
    compose "$s" up -d --wait || {
      err "${s} failed to become healthy"
      compose "$s" ps
      exit 1
    }
  else
    compose "$s" up -d
  fi
  ok "  ${s} up"
done

echo
ok "local substrate ready"
cat <<SUMMARY

  Postgres        localhost:${POSTGRES_PORT}      (${POSTGRES_USER}/${POSTGRES_PASSWORD}, db ${POSTGRES_DB})
  Kafka           localhost:${KAFKA_PORT}
  Kafka console   http://localhost:8090
  Redis           localhost:${REDIS_PORT}
  MinIO API       http://localhost:${MINIO_API_PORT}
  MinIO console   http://localhost:${MINIO_CONSOLE_PORT}  (${MINIO_ROOT_USER}/${MINIO_ROOT_PASSWORD})

  status   ./docker-all-status.sh
  logs     ./docker-all-logs.sh Kafka
  stop     ./docker-all-down.sh
SUMMARY

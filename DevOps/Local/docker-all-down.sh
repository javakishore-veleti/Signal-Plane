#!/usr/bin/env bash
# Stop the local substrate.
#
#   ./docker-all-down.sh                   stop core stacks, keep data
#   ./docker-all-down.sh all               stop everything, keep data
#   ./docker-all-down.sh --volumes         stop and delete all data
#   ./docker-all-down.sh Kafka             stop one stack
#
# --volumes is destructive and asks for confirmation, because losing the policy
# store means re-seeding tenants, subjects, and jurisdiction policy.

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_common.sh"

VOLUMES=0
KEEP_NETWORK=0
ARGS=()
for a in "$@"; do
  case "$a" in
    --volumes|-v) VOLUMES=1 ;;
    --keep-network) KEEP_NETWORK=1 ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) ARGS+=("$a") ;;
  esac
done

require_docker

declare -a STACKS
resolve_stacks STACKS "${ARGS[@]}"

if [[ $VOLUMES -eq 1 ]]; then
  warn "This deletes all local data: policy store, topics, cached decisions, stored payloads."
  read -r -p "Type 'delete' to confirm: " confirm
  [[ "$confirm" == "delete" ]] || { log "aborted"; exit 0; }
fi

for s in "${STACKS[@]}"; do
  log "stopping ${s}"
  if [[ $VOLUMES -eq 1 ]]; then
    compose "$s" down --volumes --remove-orphans
  else
    compose "$s" down --remove-orphans
  fi
  ok "  ${s} down"
done

if [[ ${#ARGS[@]} -eq 0 || "${ARGS[0]}" == "all" ]] && [[ $KEEP_NETWORK -eq 0 ]]; then
  if docker network inspect "${COMPOSE_NETWORK}" >/dev/null 2>&1; then
    if [[ -z "$(docker network inspect "${COMPOSE_NETWORK}" -f '{{range .Containers}}{{.Name}} {{end}}')" ]]; then
      docker network rm "${COMPOSE_NETWORK}" >/dev/null && dim "removed network ${COMPOSE_NETWORK}"
    else
      dim "network ${COMPOSE_NETWORK} still has attached containers, left in place"
    fi
  fi
fi

ok "done"

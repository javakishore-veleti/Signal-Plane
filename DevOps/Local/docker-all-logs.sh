#!/usr/bin/env bash
# Tail logs for one or more stacks.
#
#   ./docker-all-logs.sh Kafka
#   ./docker-all-logs.sh Postgres Redis
#   ./docker-all-logs.sh all --tail 200

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_common.sh"

TAIL=100
ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --tail) TAIL="$2"; shift 2 ;;
    -h|--help) sed -n '2,7p' "$0"; exit 0 ;;
    *) ARGS+=("$1"); shift ;;
  esac
done

require_docker

declare -a STACKS
resolve_stacks STACKS "${ARGS[@]}"

if [[ ${#STACKS[@]} -eq 1 ]]; then
  compose "${STACKS[0]}" logs -f --tail "${TAIL}"
else
  for s in "${STACKS[@]}"; do
    echo "===== ${s} ====="
    compose "$s" logs --tail "${TAIL}"
  done
fi

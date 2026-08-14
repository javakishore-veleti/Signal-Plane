#!/usr/bin/env bash
# Shared helpers for the docker-all-* scripts.
#
# The stacks are separate compose projects joined by one external network. That
# is deliberate: each substrate can be restarted, upgraded, or wiped without
# touching the others, which is what makes "Kafka is misbehaving" a two second
# fix rather than a full teardown.

set -euo pipefail

LOCAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${LOCAL_DIR}/.env"

# Start order matters only for readability; the network makes them independent.
CORE_STACKS=(Postgres Kafka Redis MinIO)
OPTIONAL_STACKS=(Observability)

# shellcheck disable=SC1090
set -a; source "${ENV_FILE}"; set +a

c_red=$'\033[31m'; c_green=$'\033[32m'; c_yellow=$'\033[33m'; c_dim=$'\033[2m'; c_off=$'\033[0m'

log()  { printf '%s\n' "$*"; }
ok()   { printf '%s%s%s\n' "$c_green" "$*" "$c_off"; }
warn() { printf '%s%s%s\n' "$c_yellow" "$*" "$c_off"; }
err()  { printf '%s%s%s\n' "$c_red" "$*" "$c_off" >&2; }
dim()  { printf '%s%s%s\n' "$c_dim" "$*" "$c_off"; }

require_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    err "docker not found on PATH"
    exit 1
  fi
  if ! docker compose version >/dev/null 2>&1; then
    err "docker compose v2 not available. This project uses 'docker compose', not 'docker-compose'."
    exit 1
  fi
  if ! docker info >/dev/null 2>&1; then
    err "docker daemon is not running"
    exit 1
  fi
}

ensure_network() {
  if ! docker network inspect "${COMPOSE_NETWORK}" >/dev/null 2>&1; then
    docker network create "${COMPOSE_NETWORK}" >/dev/null
    dim "created network ${COMPOSE_NETWORK}"
  fi
}

compose() {
  local stack="$1"; shift
  docker compose --env-file "${ENV_FILE}" -f "${LOCAL_DIR}/${stack}/docker-compose.yaml" "$@"
}

stack_exists() {
  [[ -f "${LOCAL_DIR}/$1/docker-compose.yaml" ]]
}

resolve_stacks() {
  # No arguments: core stacks only. Named arguments: exactly those.
  local -n out=$1; shift
  if [[ $# -eq 0 ]]; then
    out=("${CORE_STACKS[@]}")
    return
  fi
  out=()
  for s in "$@"; do
    if [[ "$s" == "all" ]]; then
      out=("${CORE_STACKS[@]}" "${OPTIONAL_STACKS[@]}")
      return
    fi
    if stack_exists "$s"; then
      out+=("$s")
    else
      err "unknown stack '$s'. Available: ${CORE_STACKS[*]} ${OPTIONAL_STACKS[*]}"
      exit 1
    fi
  done
}

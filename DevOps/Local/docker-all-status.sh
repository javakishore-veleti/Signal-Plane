#!/usr/bin/env bash
# Report what is running, and whether it is actually usable.
#
#   ./docker-all-status.sh            core stacks
#   ./docker-all-status.sh all        everything
#   ./docker-all-status.sh --json     machine readable
#
# Container "running" and service "usable" are different states. This reports
# health where the stack declares a health check, because a broker that is up
# but still forming will refuse connections while looking fine to docker ps.

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_common.sh"

JSON=0
ARGS=()
for a in "$@"; do
  case "$a" in
    --json) JSON=1 ;;
    -h|--help) sed -n '2,11p' "$0"; exit 0 ;;
    *) ARGS+=("$a") ;;
  esac
done

require_docker

declare -a STACKS
resolve_stacks STACKS "${ARGS[@]}"

if docker network inspect "${COMPOSE_NETWORK}" >/dev/null 2>&1; then
  NET_STATE="present"
else
  NET_STATE="absent"
fi

if [[ $JSON -eq 1 ]]; then
  printf '{"network":{"name":"%s","state":"%s"},"stacks":[' "${COMPOSE_NETWORK}" "${NET_STATE}"
  first=1
  for s in "${STACKS[@]}"; do
    ids="$(compose "$s" ps -q 2>/dev/null || true)"
    running=0; healthy=0; total=0
    for id in $ids; do
      total=$((total+1))
      st="$(docker inspect -f '{{.State.Status}}' "$id" 2>/dev/null || echo unknown)"
      hl="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$id" 2>/dev/null || echo none)"
      [[ "$st" == "running" ]] && running=$((running+1))
      [[ "$hl" == "healthy" || "$hl" == "none" ]] && healthy=$((healthy+1))
    done
    [[ $first -eq 0 ]] && printf ','
    first=0
    printf '{"stack":"%s","containers":%d,"running":%d,"healthy":%d}' "$s" "$total" "$running" "$healthy"
  done
  printf ']}\n'
  exit 0
fi

printf 'network %-18s %s\n\n' "${COMPOSE_NETWORK}" "${NET_STATE}"
printf '%-16s %-28s %-12s %-12s %s\n' STACK CONTAINER STATUS HEALTH PORTS
printf '%s\n' "-------------------------------------------------------------------------------------"

any=0
for s in "${STACKS[@]}"; do
  ids="$(compose "$s" ps -q 2>/dev/null || true)"
  if [[ -z "$ids" ]]; then
    printf '%-16s %-28s %-12s %-12s %s\n' "$s" "-" "stopped" "-" "-"
    continue
  fi
  for id in $ids; do
    any=1
    name="$(docker inspect -f '{{.Name}}' "$id" | sed 's|^/||')"
    st="$(docker inspect -f '{{.State.Status}}' "$id")"
    hl="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}-{{end}}' "$id")"
    ports="$(docker port "$id" 2>/dev/null | awk -F' -> ' '{print $2}' | tr '\n' ',' | sed 's/,$//')"
    printf '%-16s %-28s %-12s %-12s %s\n' "$s" "$name" "$st" "$hl" "${ports:--}"
  done
done

echo
if [[ $any -eq 0 ]]; then
  warn "nothing running. Start with ./docker-all-up.sh"
else
  dim "unhealthy or restarting? ./docker-all-logs.sh <Stack>"
fi

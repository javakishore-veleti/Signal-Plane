#!/usr/bin/env bash
# Destroy and rebuild the local substrate from scratch.
#
# Use when local state has diverged confusingly. Everything is re-seeded from
# DevOps/Local/Postgres/init and the Kafka and MinIO bootstrap services, so a
# reset is cheap by design.

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_common.sh"
require_docker

warn "This destroys all local data and rebuilds the substrate."
read -r -p "Type 'reset' to confirm: " confirm
[[ "$confirm" == "reset" ]] || { log "aborted"; exit 0; }

"${LOCAL_DIR}/docker-all-down.sh" all --volumes <<< "delete"
"${LOCAL_DIR}/docker-all-up.sh" all
ok "reset complete"

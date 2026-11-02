#!/usr/bin/env bash
set -euo pipefail

original_command="${1:-${SSH_ORIGINAL_COMMAND:-}}"
read -r action requested_sha extra <<< "$original_command"
if [[ "$action" != "deploy" || ! "$requested_sha" =~ ^[0-9a-f]{40}$ || -n "${extra:-}" ]]; then
  echo "Only 'deploy <40-character commit SHA>' is allowed." >&2
  exit 64
fi

cd /opt/escape-plan
exec 9>.deploy.lock
if ! flock -n 9; then
  echo "Another deployment is already running." >&2
  exit 75
fi

git fetch --prune origin main
remote_sha="$(git rev-parse origin/main)"
if [[ "$requested_sha" != "$remote_sha" ]]; then
  echo "Refusing to deploy: requested commit is not the current origin/main." >&2
  exit 65
fi

git checkout main
git reset --hard "$requested_sha"
docker compose up --build -d

domain="$(sed -n 's/^DOMAIN=//p' .env | head -n 1)"
if [[ -z "$domain" ]]; then
  echo "DOMAIN is missing from /opt/escape-plan/.env." >&2
  exit 66
fi

curl --fail --silent --show-error \
  --retry 10 --retry-delay 3 --retry-all-errors \
  "https://${domain}/api/health"
echo
docker compose ps

#!/usr/bin/env bash
# Generate HTTP basic-auth credentials for subscriber deployment.
# Usage: ./scripts/generate-subscriber-auth.sh [username] [password]
set -euo pipefail

USER="${1:-subscriber}"
PASS="${2:-}"

if [[ -z "$PASS" ]]; then
  read -rsp "Password for $USER: " PASS
  echo ""
fi

HASH="$(docker run --rm caddy:2-alpine caddy hash-password --plaintext "$PASS")"

echo ""
echo "Add to .env:"
echo "CADDY_PROFILE=subscribers"
echo "BASIC_AUTH_USER=$USER"
echo "BASIC_AUTH_HASH=$HASH"
echo ""
echo "Give subscribers: username=$USER  password=(the value you entered)"
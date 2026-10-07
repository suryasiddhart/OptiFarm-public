#!/bin/sh
# Writes the frontend runtime configuration (/config.js) from environment
# variables. Runs from /docker-entrypoint.d/ before nginx starts.
#
#   API_BASE_URL — backend base URL (default: "/api", same-origin via ingress)
set -eu

CONFIG_FILE=/usr/share/nginx/html/config.js

if [ -n "${API_BASE_URL:-}" ]; then
  # JSON-escape backslashes and double quotes
  escaped=$(printf '%s' "$API_BASE_URL" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g')
  printf 'window.__APP_CONFIG__ = { "apiBaseUrl": "%s" };\n' "$escaped" > "$CONFIG_FILE"
  echo "$0: API base URL set to $API_BASE_URL"
else
  echo "$0: API_BASE_URL not set, using default config.js"
fi

#!/bin/sh
set -eu

if [ -z "${BACKEND_URL:-}" ]; then
  echo "BACKEND_URL is required." >&2
  exit 1
fi

envsubst '${BACKEND_URL} ${API_AUTH_TOKEN}' \
  < /etc/nginx/templates/default.conf.template \
  > /etc/nginx/conf.d/default.conf

nginx -t
exec "$@"

#!/bin/sh

cat <<EOF > /app/public/env-config.js
window._env_ = {
  API_URL: "${API_URL:-http://localhost:8000}",
  WS_URL: "${WS_URL:-ws://localhost:8000}"
};
EOF

exec npm run dev

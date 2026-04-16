#!/bin/sh
set -e
# Inject runtime API URL into a JS config file loaded by index.html.
# VITE_API_URL is set as a container env var by the Helm chart.
cat > /usr/share/nginx/html/config.js <<JS
window.__ORCHESTRA_CONFIG__ = { apiUrl: "${VITE_API_URL:-}" };
JS
exec nginx -g 'daemon off;'

#!/bin/sh
set -e
# Inject runtime config into a JS config file loaded by index.html.
# VITE_API_URL / VITE_GA_MEASUREMENT_ID are set as container env vars by the
# Helm chart. An empty gaMeasurementId leaves analytics completely off.
cat > /usr/share/nginx/html/config.js <<JS
window.__ORCHESTRA_CONFIG__ = { apiUrl: "${VITE_API_URL:-}", gaMeasurementId: "${VITE_GA_MEASUREMENT_ID:-}" };
JS
exec nginx -g 'daemon off;'

"""Orchestra no-auth JupyterLab server configuration.

Authentication is handled upstream by oauth2-proxy (ingress) and the per-pod
Orchestra sidecar, so the in-pod Jupyter server runs tokenless. Do NOT use this
image outside of Orchestra (or another authenticating proxy) — it has no login.

``c`` is the Jupyter config object injected at load time by jupyter_server.
"""

# ruff: noqa: F821  (c is provided by the jupyter_server config loader)

# Disable the token/password login entirely.
c.ServerApp.token = ""
c.ServerApp.password = ""
c.IdentityProvider.token = ""  # jupyter_server >= 2.0

# We sit behind a reverse proxy (sidecar -> oauth2-proxy). Trust forwarded
# headers and relax same-origin/XSRF checks so XHR and WebSocket requests from
# the proxied origin succeed.
c.ServerApp.allow_origin = "*"
c.ServerApp.trust_xheaders = True
c.ServerApp.disable_check_xsrf = True

# Container-friendly defaults.
c.ServerApp.ip = "0.0.0.0"
c.ServerApp.open_browser = False

# Orchestra no-auth base image: JupyterLab
#
# The Jupyter server runs WITHOUT a token because every Orchestra workshop
# session is fronted by oauth2-proxy (at the ingress) and the per-pod Orchestra
# sidecar, which together enforce authentication and ownership. See
# jupyter_server_config.py for the disabled-auth settings.
#
# Do NOT run this image outside of Orchestra (or another authenticating proxy).
#
# JupyterLab listens on 8888 — set `port: 8888` in your Workshop template; the
# sidecar proxies to it on localhost.

FROM quay.io/jupyter/minimal-notebook:latest

# System-wide server config: token disabled + proxy-friendly settings.
# Written as root so it lands in /etc/jupyter, then drop back to the notebook
# user that the base image runs as.
USER root
COPY jupyter_server_config.py /etc/jupyter/jupyter_server_config.py
USER ${NB_UID}

EXPOSE 8888

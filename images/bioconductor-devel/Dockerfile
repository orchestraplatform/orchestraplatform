# check=skip=SecretsUsedInArgOrEnv
# (DISABLE_AUTH/ROOT are rocker feature flags, not secrets — the linter only
#  flags them because the name contains "AUTH".)

# Orchestra no-auth base image: Bioconductor devel (RStudio Server)
#
# RStudio Server authentication is DISABLED here on purpose. Every Orchestra
# workshop session sits behind oauth2-proxy (at the ingress) and the per-pod
# Orchestra sidecar, which together enforce authentication and ownership. A
# second login prompt inside the pod would only confuse participants.
#
# Do NOT run this image outside of Orchestra (or another authenticating proxy).
#
# RStudio listens on 8787 — set `port: 8787` in your Workshop template (this is
# also the default); the sidecar proxies to it on localhost.

FROM bioconductor/bioconductor_docker:devel

# rocker/rstudio honors these at container start:
#   DISABLE_AUTH=true -> skip the RStudio login, auto-login as user `rstudio`
#   ROOT=true         -> grant the session sudo (useful for system deps)
ENV DISABLE_AUTH=true \
    ROOT=true

EXPOSE 8787

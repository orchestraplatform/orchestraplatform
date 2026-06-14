# Orchestra workshop base images

These are **no-auth base images** for Orchestra workshop sessions. They exist so
workshop authors can build their own environments without re-solving the "how do
I disable the app's built-in login" problem every time.

## The no-auth contract

Every Orchestra workshop session is fronted by two layers that enforce
authentication and per-session ownership:

1. **oauth2-proxy** at the ingress (who are you?), and
2. the **Orchestra sidecar** in each pod (do you own this session?).

Because of that, the application inside the pod must **not** present its own
login. A second prompt would only confuse participants — and in the proxied
setup the participant often can't satisfy it anyway (e.g. a Jupyter token they
never see). These base images turn that login off.

> ⚠️ Do not run these images outside of Orchestra (or another authenticating
> proxy in front of them). They are intentionally unauthenticated.

## Images

| Directory             | Base                                      | App             | Port |
| --------------------- | ----------------------------------------- | --------------- | ---- |
| `bioconductor-devel/` | `bioconductor/bioconductor_docker:devel`  | RStudio Server  | 8787 |
| `jupyterlab/`         | `quay.io/jupyter/minimal-notebook`        | JupyterLab      | 8888 |

The port is what you set as `spec.port` on a Workshop template; the sidecar
proxies to `http://localhost:<port>`.

## Building & publishing

```sh
just workshop-images-push
```

This cross-builds both images for `linux/amd64` and pushes them to Artifact
Registry as `.../bioconductor-devel:latest` and `.../jupyterlab:latest`.

## Extending them

See **User Guide → Building Workshop Images** in the docs for how to base your
own image on these and reference it from a Workshop template.

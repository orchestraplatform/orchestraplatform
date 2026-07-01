---
title: oauth2-proxy Setup
description: Configure Google (and optionally GitHub) OAuth for Orchestra.
---

Orchestra's bundled oauth2-proxy is configured during `helm install` via the
root-level `"oauth2-proxy"` subchart values block. This page walks you through
creating the required credentials and wiring them in.

:::tip
This is the **credentials/provider reference**. It fits into
[4. Ingress, TLS & auth](/docs/deployment/ingress-tls-auth/#5-oauth2-proxy-bundled-subchart)
in the [deployment sequence](/docs/deployment/overview/).
:::

## Google OAuth (primary provider)

1. Open the [Google Cloud Console](https://console.cloud.google.com/apis/credentials).

2. Create a new **OAuth 2.0 Client ID**:
   - Application type: **Web application**
   - Name: `Orchestra`
   - Authorized redirect URIs: `https://app.<your-domain>/oauth2/callback`

3. Copy the **Client ID** and **Client secret**.

4. Store them in a Kubernetes Secret (recommended):

```bash
kubectl create secret generic orchestra-oauth-secrets \
  --namespace orchestra-system \
  --from-literal=client-id=<google-client-id> \
  --from-literal=client-secret=<google-client-secret> \
  --from-literal="cookie-secret=$(python3 -c 'import secrets; print(secrets.token_hex(16))')"
```

5. Reference the secret in your values file.

The Orchestra chart bundles
[`oauth2-proxy`](https://github.com/oauth2-proxy/manifests/tree/main/helm/oauth2-proxy)
as a subchart. All credentials and domain rules are passed straight through to
it under a **root-level `"oauth2-proxy"` key** — *not* nested under
`oauth2Proxy`. (The chart's own `oauth2Proxy` block only has `enabled` and
`fullProxy`.) Because the key contains a dot, use a values file rather than
`--set`:

```yaml
# my-values.yaml
oauth2Proxy:
  enabled: true
  fullProxy: true        # recommended for Traefik

"oauth2-proxy":          # root level — verbatim subchart values
  config:
    existingSecret: orchestra-oauth-secrets   # client-id / client-secret / cookie-secret keys
    configFile: |-
      email_domains = [ "example.edu" ]
      upstreams = [ "http://orchestra-frontend.orchestra-system.svc.cluster.local:80" ]
  extraArgs:
    redirect-url: "https://app.orchestra.example.edu/oauth2/callback"
    cookie-domain: ".orchestra.example.edu"
    whitelist-domain: ".orchestra.example.edu"
    set-xauthrequest: "true"
    skip-provider-button: "true"
```

```bash
helm install orchestra deploy/charts/orchestra \
  --set global.domain=orchestra.example.edu \
  -f my-values.yaml
```

The `existingSecret` must expose `client-id`, `client-secret`, and
`cookie-secret` keys — exactly what the Step 4 command creates.

### Restricting access

oauth2-proxy decides who may log in. There are two complementary mechanisms,
both configured on the subchart:

- **By domain** — set `email_domains` in `config.configFile`. Only addresses in
  the listed domains can authenticate:
  ```yaml
  "oauth2-proxy":
    config:
      configFile: |-
        email_domains = [ "example.edu" ]
        upstreams = [ "http://orchestra-frontend.orchestra-system.svc.cluster.local:80" ]
  ```

- **By specific email** — use `authenticatedEmailsFile.restricted_access` for an
  explicit allowlist (works alongside, or instead of, `email_domains`):
  ```yaml
  "oauth2-proxy":
    authenticatedEmailsFile:
      enabled: true
      restricted_access: |-
        alice@gmail.com
        bob@other.edu
  ```

- **Open to any Google account** (not recommended for production) — set
  `email_domains = [ "*" ]` in `config.configFile`.

## GitHub as a second provider

To accept GitHub logins in addition to Google, you need a separate
oauth2-proxy instance (oauth2-proxy supports one provider per instance).
The recommended approach for multi-provider setups is to put a Dex OIDC
broker in front of both providers.

For a simpler single-provider GitHub setup, switch the bundled subchart to the
GitHub provider in your values file:

```yaml
# values-github.yaml — GitHub-only auth
oauth2Proxy:
  enabled: true
  fullProxy: true

"oauth2-proxy":
  config:
    existingSecret: orchestra-oauth-secrets   # GitHub OAuth app client-id / client-secret + cookie-secret
    configFile: |-
      provider = "github"
      github_org = "my-org"                    # restrict to org members (optional)
      upstreams = [ "http://orchestra-frontend.orchestra-system.svc.cluster.local:80" ]
  extraArgs:
    redirect-url: "https://app.orchestra.example.edu/oauth2/callback"
    cookie-domain: ".orchestra.example.edu"
    whitelist-domain: ".orchestra.example.edu"
    set-xauthrequest: "true"
    skip-provider-button: "true"
```

Create a GitHub OAuth App at `https://github.com/settings/developers`:
- Homepage URL: `https://app.<your-domain>`
- Authorization callback URL: `https://app.<your-domain>/oauth2/callback`

## Cookie secret rotation

The cookie secret encrypts the session cookie. Rotating it invalidates all
active sessions. There is no `oauth2Proxy.config.cookieSecret` chart value — the
secret is read from the referenced `existingSecret`, so rotation means updating
that Secret's `cookie-secret` key and restarting oauth2-proxy:

```bash
NEW_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(16))")

# Update the cookie-secret key in the existing Secret in place
kubectl create secret generic orchestra-oauth-secrets \
  --namespace orchestra-system \
  --from-literal=cookie-secret="$NEW_SECRET" \
  --dry-run=client -o yaml | \
  kubectl patch secret orchestra-oauth-secrets -n orchestra-system \
    --patch-file=/dev/stdin

# Restart oauth2-proxy to pick up the new value
kubectl rollout restart deployment/orchestra-oauth2-proxy -n orchestra-system
```

(If you inline `cookieSecret` under `"oauth2-proxy".config` instead of using a
Secret, rotate by changing that value and re-running `helm upgrade`.)

## Troubleshooting

**Users see "403 Permission Denied" after login:**
The user's email doesn't match `email_domains` in `config.configFile`, or isn't
in the `authenticatedEmailsFile.restricted_access` allowlist.
Check the oauth2-proxy pod logs:
```bash
kubectl logs -n orchestra-system -l app.kubernetes.io/name=oauth2-proxy --tail=50
```

**Redirect loop / infinite redirects:**
The callback URL registered in Google doesn't match `https://app.<domain>/oauth2/callback`.
Verify `global.domain` matches the URL you registered.

**API returns 401 after frontend loads:**
The Traefik ForwardAuth middleware may not be wired to the API ingress.
Check that both `orchestra-auth` and `orchestra-auth-headers` middlewares
appear in the API ingress annotations:
```bash
kubectl get ingress orchestra-api -n orchestra-system -o yaml
```

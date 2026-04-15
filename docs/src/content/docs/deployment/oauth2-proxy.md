---
title: oauth2-proxy Setup
description: Configure Google (and optionally GitHub) OAuth for Orchestra.
---

Orchestra's bundled oauth2-proxy is configured during `helm install`. This
page walks you through creating the required credentials.

## Google OAuth (primary provider)

1. Open the [Google Cloud Console](https://console.cloud.google.com/apis/credentials).

2. Create a new **OAuth 2.0 Client ID**:
   - Application type: **Web application**
   - Name: `Orchestra`
   - Authorized redirect URIs: `https://app.<your-domain>/oauth2/callback`

3. Copy the **Client ID** and **Client secret**.

4. Pass them to Helm:

```bash
helm install orchestra deploy/charts/orchestra \
  --set global.domain=orchestra.example.edu \
  --set oauth2Proxy.config.clientID=<client-id> \
  --set oauth2Proxy.config.clientSecret=<client-secret> \
  --set oauth2Proxy.config.cookieSecret=$(python3 -c "import secrets; print(secrets.token_hex(16))") \
  --set "oauth2Proxy.config.allowedDomains={example.edu}"
```

### Restricting access

- **By domain** — only emails ending in `@example.edu` can log in:
  ```yaml
  oauth2Proxy:
    config:
      allowedDomains:
        - example.edu
  ```

- **By specific email** — regardless of domain:
  ```yaml
  oauth2Proxy:
    config:
      allowedEmails:
        - alice@gmail.com
        - bob@other.edu
  ```

- **Open to any Google account** (not recommended for production):
  ```yaml
  oauth2Proxy:
    config:
      allowedDomains:
        - "*"
  ```

## GitHub as a second provider

To accept GitHub logins in addition to Google, you need a separate
oauth2-proxy instance (oauth2-proxy supports one provider per instance).
The recommended approach for multi-provider setups is to put a Dex OIDC
broker in front of both providers.

For a simpler single-provider GitHub setup, replace the Google provider
configuration in your `values-prod.yaml`:

```yaml
# values-github.yaml — GitHub-only auth
oauth2Proxy:
  enabled: true
  config:
    clientID: <github-oauth-app-client-id>
    clientSecret: <github-oauth-app-client-secret>
    cookieSecret: <16-byte-hex>
    # Restrict to members of a GitHub org (optional)
    githubOrg: my-org
```

Create a GitHub OAuth App at `https://github.com/settings/developers`:
- Homepage URL: `https://app.<your-domain>`
- Authorization callback URL: `https://app.<your-domain>/oauth2/callback`

## Cookie secret rotation

The cookie secret encrypts the session cookie. Rotating it invalidates all
active sessions:

```bash
NEW_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(16))")
helm upgrade orchestra deploy/charts/orchestra \
  --set oauth2Proxy.config.cookieSecret=$NEW_SECRET \
  --reuse-values
```

## Troubleshooting

**Users see "403 Permission Denied" after login:**
The user's email doesn't match `allowedDomains` or `allowedEmails`.
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

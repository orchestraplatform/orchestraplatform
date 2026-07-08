#!/usr/bin/env bash
# =============================================================================
# scripts/doctor.sh — Orchestra deployment preflight
#
# READ-ONLY. This script never mutates cluster or cloud state. It only runs
# describe/get/version/lint/template commands and parses local files. Run it
# before and after a deploy to catch the environment interdependencies that
# make an Orchestra install fail *at runtime* instead of discovering them live.
#
# Each check prints a PASS / WARN / FAIL line with a concrete one-line fix on
# anything that isn't PASS, grouped under "==> [n/N]" headers. It degrades
# gracefully: if kubectl/gcloud/helm or a cluster context isn't available, the
# affected check WARNs (with why) rather than crashing, and the static checks
# (helm lint, schema sync, template resource-limit parse, ephemeral-vs-template)
# still run. Exits non-zero if any check FAILs.
#
# Dedup policy (issue #50): checks that only need kubectl/helm stay
# self-contained here, so a bare-cluster operator can run them without the dev
# toolchain. Checks that REQUIRE the dev toolchain regardless (schema
# regeneration needs uv + the template-tools package — unrunnable on a bare
# cluster either way) delegate to their single `just` implementation and SKIP
# with a message when just/uv is absent, rather than reimplementing it.
#
# Usage:
#   just doctor                       # current kubectl context
#   context=my-ctx just doctor        # override the kube context
#   KUBECONFIG=/path just doctor      # or point at a specific kubeconfig
#
# Checks:
#   [1] Tooling + cluster reachability
#   [2] Node egress for external image pulls (public nodes OR Cloud NAT)
#   [3] Ephemeral-storage headroom vs workshop templates
#   [4] Rendered container requests <= limits (Autopilot hides this; Standard rejects)
#   [5] External dependencies (IngressClass, cert-manager CRDs, oauth2-proxy)
#   [6] Required secrets/config (DB url/secret, oauth2-proxy client secret)
#   [7] Chart sanity (helm lint, template schema in sync)
#   [8] Migrate-hook prerequisites (namespace, DB reachable before install)
# =============================================================================
set -uo pipefail

# --- Repo root (this script lives in scripts/) -------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

CHART="deploy/charts/orchestra"
TEMPLATES_DIR="$CHART/files/templates"
GCP_VALUES="deploy/gcp-values.yaml"
GCP_SECRETS="deploy/gcp-values-secrets.yaml"
NAMESPACE="${namespace:-orchestra-system}"

# --- Colors (only when stdout is a tty) --------------------------------------
if [ -t 1 ]; then
    C_RED=$'\033[31m'; C_GRN=$'\033[32m'; C_YEL=$'\033[33m'; C_BLU=$'\033[34m'; C_RST=$'\033[0m'
else
    C_RED=""; C_GRN=""; C_YEL=""; C_BLU=""; C_RST=""
fi

FAIL_COUNT=0
WARN_COUNT=0
PASS_COUNT=0

pass() { printf "  %sPASS%s %s\n" "$C_GRN" "$C_RST" "$1"; PASS_COUNT=$((PASS_COUNT+1)); }
warn() { printf "  %sWARN%s %s\n" "$C_YEL" "$C_RST" "$1"; [ -n "${2:-}" ] && printf "       ↳ fix: %s\n" "$2"; WARN_COUNT=$((WARN_COUNT+1)); }
fail() { printf "  %sFAIL%s %s\n" "$C_RED" "$C_RST" "$1"; [ -n "${2:-}" ] && printf "       ↳ fix: %s\n" "$2"; FAIL_COUNT=$((FAIL_COUNT+1)); }
info() { printf "  %s•%s    %s\n" "$C_BLU" "$C_RST" "$1"; }
hdr()  { printf "\n%s==> [%s]%s %s\n" "$C_BLU" "$1" "$C_RST" "$2"; }

# --- kubectl wrapper honoring context= just-var ------------------------------
KUBECTL=(kubectl)
if [ -n "${context:-}" ]; then
    KUBECTL=(kubectl --context "$context")
fi
k() { "${KUBECTL[@]}" "$@"; }

have() { command -v "$1" >/dev/null 2>&1; }

# Cluster reachability, cached for later checks.
CLUSTER_OK=0
cluster_reachable() {
    have kubectl || return 1
    k cluster-info >/dev/null 2>&1
}

TOTAL=8

# =============================================================================
hdr "1/$TOTAL" "Tooling present + cluster reachable"
# =============================================================================
for bin in kubectl helm; do
    if have "$bin"; then pass "$bin found ($(command -v "$bin"))"
    else fail "$bin not found on PATH" "install $bin (see docs/deployment/)"; fi
done
if have jq; then pass "jq found"; else warn "jq not found" "install jq (some checks fall back to coarser parsing)"; fi

if cluster_reachable; then
    CLUSTER_OK=1
    CTX="$(k config current-context 2>/dev/null || echo '?')"
    SRV="$(k cluster-info 2>/dev/null | sed -n '1s/.*running at //p')"
    pass "cluster reachable — context '$CTX' ($SRV)"
    # gcloud only matters for GKE contexts.
    if printf '%s' "$CTX" | grep -qi 'gke'; then
        if have gcloud; then pass "gcloud found (GKE context)"
        else warn "gcloud not found but context looks like GKE" "install the gcloud CLI for GKE-specific checks (egress/NAT)"; fi
    fi
else
    if ! have kubectl; then
        warn "kubectl absent — cluster checks skipped" "install kubectl"
    else
        warn "kubectl cannot reach a cluster — cluster checks will be skipped" \
             "set a context (context=<name> just doctor) or export KUBECONFIG; static checks still run"
    fi
fi

# =============================================================================
hdr "2/$TOTAL" "Node egress for external image pulls (Docker Hub / quay.io / registry.k8s.io)"
# =============================================================================
# Workshops pull rocker/rstudio (Docker Hub), jupyter (quay.io) and the pause
# image (registry.k8s.io). Public nodes egress directly; private nodes need a
# Cloud NAT or every workshop pod hangs in ImagePullBackOff.
if [ "$CLUSTER_OK" -eq 1 ]; then
    NODE_JSON="$(k get nodes -o json 2>/dev/null)"
    if [ -z "$NODE_JSON" ]; then
        warn "could not list nodes" "check RBAC: kubectl auth can-i list nodes"
    elif have jq; then
        NODE_COUNT=$(printf '%s' "$NODE_JSON" | jq '.items | length')
        EXT_COUNT=$(printf '%s' "$NODE_JSON" | jq '[.items[] | select(.status.addresses[]? | select(.type=="ExternalIP") | .address != "" and .address != null)] | length')
        if [ "$EXT_COUNT" -gt 0 ]; then
            pass "$EXT_COUNT/$NODE_COUNT node(s) have external IPs (public nodes egress directly)"
        else
            # Private nodes — need a Cloud NAT for the cluster's network/region.
            NAT_OK=""
            if have gcloud; then
                REGION="$(k config current-context 2>/dev/null | sed -nE 's/^gke_[^_]+_([a-z0-9-]+)_.*/\1/p' | sed -E 's/-[a-z]$//')"
                if [ -n "$REGION" ]; then
                    NAT_LIST="$(gcloud compute routers list --format='value(region)' 2>/dev/null | grep -i "$REGION" || true)"
                    [ -n "$NAT_LIST" ] && NAT_OK="1"
                fi
            fi
            if [ -n "$NAT_OK" ]; then
                pass "private nodes but a Cloud Router/NAT exists in the cluster region ($REGION)"
            else
                fail "private nodes and no Cloud NAT detected — external image pulls will hang in ImagePullBackOff" \
                     "set enable_private_nodes=false in deploy/tofu OR add a Cloud NAT for the cluster's network/region"
            fi
        fi
    else
        # No jq: coarse grep on wide output.
        if k get nodes -o wide 2>/dev/null | awk 'NR>1{print $7}' | grep -qvE '^(<none>|)$'; then
            pass "node(s) appear to have external IPs (public nodes)"
        else
            warn "cannot confirm node egress without jq" "install jq, or verify a Cloud NAT exists for private nodes"
        fi
    fi
else
    warn "no cluster — egress/NAT check skipped" "run against the target cluster before deploying workshops"
fi

# =============================================================================
hdr "3/$TOTAL" "Ephemeral-storage headroom vs workshop templates"
# =============================================================================
# Parse each template's resources.ephemeralStorage(Request) and compare the max
# against a tenant node's *allocatable* ephemeral-storage. A 30GB NAP boot disk
# yields only ~7.8GiB allocatable — below the 8Gi the templates request — so the
# scheduler can't place the pod (or the kubelet evicts it). Bump the disk.
to_bytes() {
    # e.g. 8Gi -> bytes, 8397760472 -> bytes. Handles Ki/Mi/Gi/Ti + K/M/G/T + raw.
    python3 - "$1" <<'PY'
import sys,re
s=str(sys.argv[1]).strip()
m=re.match(r'^([0-9.]+)\s*([KMGT]i?)?$',s)
if not m:
    print(-1); sys.exit()
n=float(m.group(1)); u=m.group(2) or ''
mul={'':1,'K':1e3,'M':1e6,'G':1e9,'T':1e12,'Ki':1024,'Mi':1024**2,'Gi':1024**3,'Ti':1024**4}
print(int(n*mul.get(u,1)))
PY
}
human_gib() { python3 -c "import sys; b=int(sys.argv[1]); print(f'{b/1024**3:.1f}GiB')" "$1"; }

MAX_TPL_REQ=0
MAX_TPL_STR="0"
MAX_TPL_FILE=""
if [ -d "$TEMPLATES_DIR" ]; then
    for f in "$TEMPLATES_DIR"/*.yaml; do
        [ -f "$f" ] || continue
        # Prefer the request field; fall back to the limit if request is absent.
        val="$(python3 - "$f" <<'PY'
import sys,yaml
try:
    d=yaml.safe_load(open(sys.argv[1])) or {}
except Exception:
    sys.exit()
r=(d.get('resources') or {})
v=r.get('ephemeralStorageRequest') or r.get('ephemeralStorage')
if v: print(v)
PY
)"
        [ -z "$val" ] && continue
        b="$(to_bytes "$val")"
        if [ "$b" -gt "$MAX_TPL_REQ" ]; then
            MAX_TPL_REQ="$b"; MAX_TPL_STR="$val"; MAX_TPL_FILE="$(basename "$f")"
        fi
    done
    if [ "$MAX_TPL_REQ" -gt 0 ]; then
        info "max template ephemeral-storage request: $MAX_TPL_STR ($MAX_TPL_FILE)"
    else
        warn "no ephemeralStorage(Request) found in templates" "add resources.ephemeralStorageRequest to templates so the scheduler reserves disk"
    fi
else
    warn "templates dir $TEMPLATES_DIR not found" "run from the repo root"
fi

if [ "$CLUSTER_OK" -eq 1 ] && [ "$MAX_TPL_REQ" -gt 0 ]; then
    # Allocatable ephemeral-storage of a tenant node (compute-class label set),
    # else the min allocatable across all nodes as a conservative proxy.
    # allocatable ephemeral-storage may be raw bytes (e.g. 8397760472) or a
    # quantity with a binary/decimal suffix (e.g. 7897760Ki). Normalise with the
    # same to_bytes() used for template requests, taking the *smallest* node.
    TENANT_ALLOC=""
    min_alloc_bytes() {
        local selector=("$@") vals v b min=""
        vals="$(k get nodes "${selector[@]}" -o jsonpath='{range .items[*]}{.status.allocatable.ephemeral-storage}{"\n"}{end}' 2>/dev/null)"
        [ -z "$vals" ] && return 1
        while IFS= read -r v; do
            [ -z "$v" ] && continue
            b="$(to_bytes "$v")"
            [ "$b" -le 0 ] 2>/dev/null && continue
            if [ -z "$min" ] || [ "$b" -lt "$min" ]; then min="$b"; fi
        done <<< "$vals"
        [ -n "$min" ] && { printf '%s' "$min"; return 0; } || return 1
    }
    if TENANT_ALLOC="$(min_alloc_bytes -l cloud.google.com/compute-class)"; then
        SRC="tenant node (compute-class labelled)"
    elif TENANT_ALLOC="$(min_alloc_bytes)"; then
        SRC="smallest node (no compute-class-labelled tenant node found)"
    else
        TENANT_ALLOC=""
    fi
    if [ -n "$TENANT_ALLOC" ]; then
        if [ "$TENANT_ALLOC" -ge "$MAX_TPL_REQ" ]; then
            pass "$SRC allocatable $(human_gib "$TENANT_ALLOC") >= template request $MAX_TPL_STR"
        else
            fail "template requests $MAX_TPL_STR but $SRC allocatable is only $(human_gib "$TENANT_ALLOC") — pod won't schedule / gets evicted" \
                 "bump nap_boot_disk_size_gb in deploy/tofu (30GB→50GB gives ~18GiB allocatable) OR lower the template's ephemeralStorageRequest"
        fi
    else
        warn "could not read node allocatable ephemeral-storage" \
             "a 30GB NAP boot disk yields only ~7.8GiB allocatable (< the $MAX_TPL_STR templates request); confirm nap_boot_disk_size_gb"
    fi
elif [ "$MAX_TPL_REQ" -gt 0 ]; then
    warn "no cluster — cannot compare against node allocatable" \
         "templates request $MAX_TPL_STR; a 30GB NAP boot disk gives only ~7.8GiB allocatable — size tenant disks >= $MAX_TPL_STR"
fi

# =============================================================================
hdr "4/$TOTAL" "Rendered container requests <= limits (Autopilot hides this; Standard rejects)"
# =============================================================================
# helm template the chart with GCP values (if present) and flag any container
# whose request exceeds its limit. Tonight this bit frontend + oauth2-proxy.
RENDER_ARGS=(-f "$CHART/values.yaml")
[ -f "$GCP_VALUES" ] && RENDER_ARGS+=(-f "$GCP_VALUES")
[ -f "$GCP_SECRETS" ] && RENDER_ARGS+=(-f "$GCP_SECRETS")
# Give the DB a value so the render doesn't fail on a required field.
RENDER_ARGS+=(--set api.database.url="postgresql+asyncpg://doctor@localhost:5432/doctor")

if have helm; then
    RENDERED="$(helm template orchestra "$CHART" "${RENDER_ARGS[@]}" 2>/tmp/doctor-helm-err)"
    if [ -z "$RENDERED" ]; then
        warn "helm template produced no output" "see: $(cat /tmp/doctor-helm-err | head -1)"
    else
        RENDER_TMP="$(mktemp)"; printf '%s' "$RENDERED" > "$RENDER_TMP"
        OFFENDERS="$(python3 - "$RENDER_TMP" <<'PY'
import sys,yaml,re
def to_milli(v):
    v=str(v)
    if v.endswith('m'): return float(v[:-1])
    return float(v)*1000
def to_bytes(v):
    v=str(v); m=re.match(r'^([0-9.]+)\s*([KMGTPE]i?)?$',v)
    if not m: return None
    n=float(m.group(1)); u=m.group(2) or ''
    mul={'':1,'K':1e3,'M':1e6,'G':1e9,'T':1e12,'Ki':1024,'Mi':1024**2,'Gi':1024**3,'Ti':1024**4}
    return n*mul.get(u,1)
bad=[]
for doc in yaml.safe_load_all(open(sys.argv[1]).read()):
    if not isinstance(doc,dict): continue
    kind=doc.get('kind')
    spec=doc.get('spec',{}) or {}
    # PodTemplateSpec lives under spec.template.spec (Deployment/Job/StatefulSet/
    # etc.) or is spec itself for a bare Pod.
    podspec=(spec.get('template',{}) or {}).get('spec')
    if not podspec and kind=='Pod':
        podspec=spec
    if not podspec: continue
    name=doc.get('metadata',{}).get('name','?')
    containers=(podspec.get('containers') or [])+(podspec.get('initContainers') or [])
    for c in containers:
        res=c.get('resources') or {}
        req=res.get('requests') or {}; lim=res.get('limits') or {}
        for key,conv in (('cpu',to_milli),('memory',to_bytes)):
            if key in req and key in lim:
                rv=conv(req[key]); lv=conv(lim[key])
                if rv is not None and lv is not None and rv>lv:
                    bad.append(f"{kind}/{name} container '{c.get('name','?')}': {key} request {req[key]} > limit {lim[key]}")
for b in sorted(set(bad)): print(b)
PY
)"
        rm -f "$RENDER_TMP"
        if [ -z "$OFFENDERS" ]; then
            pass "all rendered containers have requests <= limits"
        else
            while IFS= read -r line; do
                [ -n "$line" ] && fail "$line"
            done <<< "$OFFENDERS"
            info "fix: raise the limit (or lower the request) in values so request <= limit — Standard/GKE rejects request>limit"
        fi
    fi
else
    warn "helm absent — request<=limit render check skipped" "install helm"
fi

# =============================================================================
hdr "5/$TOTAL" "External dependencies the chart assumes exist"
# =============================================================================
# Resolve the configured ingress class name and whether oauth2-proxy is bundled.
ING_CLASS="$(python3 -c "import yaml,sys;
d=yaml.safe_load(open('$GCP_VALUES')) if __import__('os').path.exists('$GCP_VALUES') else {}
b=yaml.safe_load(open('$CHART/values.yaml'))
print((d.get('ingress',{}) or {}).get('className') or (b.get('ingress',{}) or {}).get('className') or 'traefik')" 2>/dev/null || echo traefik)"

# Whether oauth2-proxy is bundled (enabled by default). Computed unconditionally
# here so check [6] can reference it even when no cluster is reachable.
O2P_ENABLED="$(python3 -c "import yaml,os;
d=yaml.safe_load(open('$GCP_VALUES')) if os.path.exists('$GCP_VALUES') else {}
b=yaml.safe_load(open('$CHART/values.yaml'))
print((d.get('oauth2Proxy',{}) or {}).get('enabled', (b.get('oauth2Proxy',{}) or {}).get('enabled', True)))" 2>/dev/null || echo True)"

if [ "$CLUSTER_OK" -eq 1 ]; then
    if k get ingressclass "$ING_CLASS" >/dev/null 2>&1; then
        pass "IngressClass '$ING_CLASS' present"
    else
        warn "IngressClass '$ING_CLASS' not found" "install the ingress controller (e.g. helm install traefik traefik/traefik) or set ingress.className to an existing class"
    fi

    if k get crd certificates.cert-manager.io >/dev/null 2>&1; then
        pass "cert-manager CRDs present (certificates.cert-manager.io)"
    else
        warn "cert-manager CRDs missing" "install cert-manager (kubectl apply -f https://github.com/cert-manager/cert-manager/releases/latest/download/cert-manager.yaml) — TLS clusterIssuer refs will otherwise fail"
    fi

    # oauth2-proxy: bundled as a subchart (enabled by default) => a Deployment
    # named *oauth2-proxy* should exist post-install. Only warn if enabled and
    # nothing is found (pre-install this is expected).
    if [ "$O2P_ENABLED" = "True" ]; then
        if k get deploy -n "$NAMESPACE" 2>/dev/null | grep -qi oauth2-proxy; then
            pass "oauth2-proxy Deployment present in $NAMESPACE (bundled subchart)"
        else
            warn "oauth2Proxy enabled but no oauth2-proxy Deployment in $NAMESPACE yet" "expected after a successful install; if you bring your own proxy set oauth2Proxy.enabled=false"
        fi
    else
        info "oauth2Proxy disabled — bring-your-own auth proxy must forward X-Auth-Request-Email"
    fi
else
    warn "no cluster — dependency presence (IngressClass/cert-manager/oauth2-proxy) skipped" "run against the target cluster"
fi

# =============================================================================
hdr "6/$TOTAL" "Required secrets / config present"
# =============================================================================
# DB config: either an existingSecret reachable in-cluster, or api.database.url.
DB_SECRET="$(python3 -c "import yaml,os;
d=yaml.safe_load(open('$GCP_VALUES')) if os.path.exists('$GCP_VALUES') else {}
b=yaml.safe_load(open('$CHART/values.yaml'))
db=(d.get('api',{}) or {}).get('database') or (b.get('api',{}) or {}).get('database') or {}
print(db.get('existingSecret') or '')" 2>/dev/null || echo '')"
DB_URL="$(python3 -c "import yaml,os;
d=yaml.safe_load(open('$GCP_VALUES')) if os.path.exists('$GCP_VALUES') else {}
b=yaml.safe_load(open('$CHART/values.yaml'))
db=(d.get('api',{}) or {}).get('database') or (b.get('api',{}) or {}).get('database') or {}
print(db.get('url') or '')" 2>/dev/null || echo '')"

if [ -n "$DB_URL" ]; then
    pass "api.database.url is set in values"
elif [ -n "$DB_SECRET" ]; then
    if [ "$CLUSTER_OK" -eq 1 ]; then
        if k get secret "$DB_SECRET" -n "$NAMESPACE" >/dev/null 2>&1; then
            pass "DB secret '$DB_SECRET' present in $NAMESPACE"
        else
            fail "api.database.existingSecret='$DB_SECRET' but that secret is missing in $NAMESPACE — the pre-install migrate hook will fail" \
                 "kubectl create secret generic $DB_SECRET -n $NAMESPACE --from-literal=database-url='postgresql+asyncpg://user:pass@host:5432/db'"
        fi
    else
        warn "DB relies on existingSecret '$DB_SECRET' (cannot verify without a cluster)" "ensure secret '$DB_SECRET' exists in $NAMESPACE before install"
    fi
else
    fail "no DB config: neither api.database.url nor api.database.existingSecret is set" \
         "set api.database.existingSecret (recommended) or api.database.url in your values"
fi

# oauth2-proxy client secret: the gitignored secrets file OR an in-cluster secret.
if [ "$O2P_ENABLED" = "True" ]; then
    if [ -f "$GCP_SECRETS" ]; then
        pass "oauth2-proxy secrets file present ($GCP_SECRETS)"
    elif [ "$CLUSTER_OK" -eq 1 ] && k get secret -n "$NAMESPACE" 2>/dev/null | grep -qiE 'oauth'; then
        pass "oauth2-proxy secret present in $NAMESPACE"
    else
        warn "oauth2-proxy enabled but no $GCP_SECRETS and no in-cluster oauth secret found" \
             "create deploy/gcp-values-secrets.yaml with clientID/clientSecret/cookieSecret (see docs/deployment/gcp.mdx), or pre-create the secret"
    fi
fi

# =============================================================================
hdr "7/$TOTAL" "Chart sanity (helm lint + template schema in sync)"
# =============================================================================
if have helm; then
    if helm lint "$CHART" >/tmp/doctor-lint 2>&1; then
        pass "helm lint $CHART passes"
    else
        fail "helm lint $CHART failed" "see: $(grep -m1 -iE 'error|\[ERROR\]' /tmp/doctor-lint || echo 'run: helm lint '"$CHART")"
    fi
else
    warn "helm absent — helm lint skipped" "install helm"
fi

# Template schema drift: delegate to the single implementation (`just
# check-schema`, also the CI gate). It needs the dev toolchain (uv +
# template-tools) that a bare-cluster operator won't have, so SKIP rather than
# reimplement when just/uv is absent — see the dedup policy in the header.
if have just && have uv; then
    if just check-schema >/tmp/doctor-schema-err 2>&1; then
        pass "template.schema.json in sync with the model"
    else
        # Non-zero can mean drift OR a broken invocation — don't assert which;
        # surface the recipe's own last line so the operator sees the cause.
        fail "template-schema check failed: $(tail -n1 /tmp/doctor-schema-err 2>/dev/null)" "if stale: 'just template-schema' and commit; full output: /tmp/doctor-schema-err"
    fi
else
    warn "skipping template-schema sync check" "needs 'just' + 'uv' (dev toolchain) — run 'just check-schema' directly"
fi

# =============================================================================
hdr "8/$TOTAL" "Migrate-hook prerequisites (fresh install)"
# =============================================================================
# The pre-install/pre-upgrade migrate Job runs alembic against the DB *before*
# the app installs. If the namespace is absent (and you don't pass
# --create-namespace) or the DB is unreachable, the hook fails and the whole
# install rolls back. This is informational: confirm both up front.
if [ "$CLUSTER_OK" -eq 1 ]; then
    if k get ns "$NAMESPACE" >/dev/null 2>&1; then
        pass "namespace '$NAMESPACE' exists"
    else
        warn "namespace '$NAMESPACE' does not exist" "pass --create-namespace to helm (the deploy recipes already do) or pre-create it"
    fi
    info "the pre-install migrate hook needs the DB reachable at install time"
    if k get job -n "$NAMESPACE" 2>/dev/null | grep -q orchestra-migrate; then
        # Report the latest migrate job status if one exists.
        MJ="$(k get job -n "$NAMESPACE" -o json 2>/dev/null | jq -r '[.items[] | select(.metadata.name|test("orchestra-migrate"))] | sort_by(.metadata.creationTimestamp) | last | "\(.metadata.name) succeeded=\(.status.succeeded // 0) failed=\(.status.failed // 0)"' 2>/dev/null)"
        [ -n "$MJ" ] && info "last migrate job: $MJ"
    fi
    # Best-effort: has the DB secret (checked in [6]) — a green [6] implies the
    # hook can resolve the URL. Actual reachability can't be probed read-only.
else
    warn "no cluster — migrate-hook prerequisites not verified" "before a fresh install: ensure namespace exists (or --create-namespace) and the DB is reachable"
fi

# =============================================================================
# Summary
# =============================================================================
printf "\n%s────────────────────────────────────────────────────────%s\n" "$C_BLU" "$C_RST"
printf "  %sPASS %d%s   %sWARN %d%s   %sFAIL %d%s\n" \
    "$C_GRN" "$PASS_COUNT" "$C_RST" "$C_YEL" "$WARN_COUNT" "$C_RST" "$C_RED" "$FAIL_COUNT" "$C_RST"
if [ "$FAIL_COUNT" -gt 0 ]; then
    printf "  %s✗ deployment preflight FAILED — fix the FAIL items above before deploying.%s\n" "$C_RED" "$C_RST"
    exit 1
elif [ "$WARN_COUNT" -gt 0 ]; then
    printf "  %s✓ no hard failures — review WARN items (some may be expected pre-install).%s\n" "$C_YEL" "$C_RST"
    exit 0
else
    printf "  %s✓ all checks passed.%s\n" "$C_GRN" "$C_RST"
    exit 0
fi

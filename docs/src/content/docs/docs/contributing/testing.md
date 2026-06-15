---
title: Testing Guide
description: Unit, integration, and E2E test strategy for Orchestra.
---

Orchestra has three test tiers. Use the right tier for the right question.

## Tier 1 — Unit tests (server)

**Where:** `server/tests/` (excluding `integration/`)

**Run:**
```bash
cd server
just test          # all unit tests
just test-cov      # with coverage report
```

**What they cover:**
- FastAPI route responses (status codes, response body shape)
- Auth dependency logic (`get_current_user`): header trust, dev bypass, admin flag
- Ownership isolation (alice can't see bob's workshop)
- Workshop validation (RFC 1123 name rules, pagination bounds)
- Service layer logic with mocked Kubernetes API

**Fixture model:** The Kubernetes `CustomObjectsAPI` is mocked via
`unittest.mock.patch` in `conftest.py`. The `get_current_user` FastAPI
dependency is overridden with `app.dependency_overrides[get_current_user]`
so tests can inject any identity without a running proxy.

```python
# conftest.py pattern — inject a test identity
app.dependency_overrides[get_current_user] = lambda: CurrentUser(
    email="alice@test.example.com", is_admin=False
)
```

For tests that exercise the real auth dependency (no override), use the
`raw_client` fixture which removes any override:
```python
app.dependency_overrides.pop(get_current_user, None)
```

**When to add a unit test:** Any time you add or change a route, a
dependency, a model validator, or service logic.

---

## Tier 2 — Integration tests (server + k8s + mock OIDC)

**Where:** `server/tests/integration/`

**Run:**
```bash
cd server
just test-integration   # requires ORCHESTRA_INTEGRATION_TESTS=1
```

**Prerequisites:**
1. `kind create cluster`
2. `helm install orchestra-crds deploy/charts/orchestra-crds`
3. A mock OIDC provider (Dex or similar) running locally
4. `ORCHESTRA_INTEGRATION_TESTS=1` env var set

**What they cover:**
- Workshop CR actually written to Kubernetes with correct `spec.owner`
- Label selector filtering returns the right workshops
- Trust boundary: requests without a proxy session cookie are rejected

**Status:** The test file `test_workshop_lifecycle.py` contains commented
specifications. These will be uncommented when the kind + mock OIDC fixtures
are built out. The scaffolding (`conftest.py` skip guard, `just test-integration`
target) is in place.

**When to add an integration test:** When a bug requires both the API and
Kubernetes to reproduce, or when a CRD schema change could break the
API↔operator contract.

---

## Tier 3 — E2E tests (browser + full stack)

**Where:** `frontend/tests/e2e/`

**Run:**
```bash
cd frontend
npm run test:e2e
```

**Prerequisites:**
- Full stack deployed: kind + `orchestra-crds` + `orchestra` helm chart
- A mock OIDC provider wired in (so tests can log in without real Google)
- `PLAYWRIGHT_BASE_URL` set to the frontend URL (default: `https://app.orchestra.localhost`)

**What they cover:**
- Unauthenticated user redirected to `/oauth2/start`
- Logged-in user can create and see their workshops
- Alice's workshops invisible to Bob
- Logout clears the session

**Status:** `auth.spec.ts` contains four `.skip()` scenarios, documented as
specifications. Unskip them once the stack is running in CI.

**When to add an E2E test:** Authentication flows, login/logout, and any
feature where the security guarantee requires the full browser→proxy→API→k8s
chain to be exercised.

---

## Decision guide

| Question | Use |
|---|---|
| Does this route return the right status code? | Unit |
| Does auth reject missing / forged headers? | Unit (real auth dep) |
| Does alice's label selector filter her workshops? | Unit |
| Does the CRD schema accept/reject a given spec? | Integration |
| Does the CR appear in k8s with the right owner? | Integration |
| Does the browser redirect to Google login? | E2E |
| Does logout actually clear the cookie? | E2E |

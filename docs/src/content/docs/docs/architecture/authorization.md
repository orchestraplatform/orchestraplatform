---
title: Authorization
description: Workshop ownership model and admin access in Orchestra.
---

Once a user is [authenticated](./authentication), Orchestra applies two
authorization rules to workshop operations:

1. **Ownership** — users can only see and manage workshops they created.
2. **Admin bypass** — users whose email is in `ORCHESTRA_ADMIN_EMAILS` can
   operate on any workshop regardless of owner.

## Workshop ownership

Every workshop has a `spec.owner` field containing the email of the user who
created it. This field is:

- **Stamped at create time** by the API from the authenticated user's email.
  Callers cannot set it themselves.
- **Immutable** — the CRD schema includes a CEL validation rule
  (`self.owner == oldSelf.owner`) that prevents the field from changing after
  creation.
- **Reflected in responses** — `WorkshopResponse.owner` is always the creator's
  email.

For efficient server-side filtering, the API also stamps a label on the Workshop CR:

```
orchestra.io/owner-hash: <sha256(email)[:63]>
```

Labels cannot contain `@`, so the email is hashed. The `spec.owner` field
stores the original email and is the source of truth.

## Route behaviour

| Operation | Regular user | Admin |
|---|---|---|
| `POST /templates/` | Creates workshop with `owner = self` | Same |
| `GET /templates/` | Lists only workshops where `owner = self` | Lists all workshops |
| `GET /templates/{name}` | 200 if owner matches, **404** otherwise | 200 always |
| `DELETE /templates/{name}` | Deletes if owner matches, **404** otherwise | Deletes always |

Returning `404` (not `403`) for another user's workshop prevents leaking
information about which workshops exist. An attacker cannot distinguish "this
workshop doesn't exist" from "this workshop exists but belongs to someone else."

## Admin access

Admin status is determined at request time by checking whether
`current_user.email` is in the `ORCHESTRA_ADMIN_EMAILS` list (comma-separated,
set via Helm value `api.adminEmails`). There is no database — the list is
configuration.

Admins are also shown an **admin badge** in the frontend header.

### Granting admin access

```yaml
# values-prod.yaml
api:
  adminEmails:
    - sean@example.edu
    - ops@example.edu
```

Then `helm upgrade orchestra deploy/charts/orchestra -f values-prod.yaml`.

## Future RBAC direction

The current model (owner + admin list) is intentionally simple. Planned
extensions (tracked separately):

- **Namespace isolation** — workshop namespaces mapped to courses or cohorts.
- **Group memberships** — read group claims from the OIDC token to grant
  workshop access to teaching assistants.
- **DB-backed roles** — once group/sharing requirements outgrow a config list.

See [ADR-0002](../adr/0002-spec-owner-on-crd) for the reasoning behind the
current approach.

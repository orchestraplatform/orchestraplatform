---
title: Authorization
description: Workshop ownership model and admin access in Orchestra.
---

Once a user is [authenticated](./authentication), Orchestra applies its
authorization rules across two distinct resources — **templates** and
**instances** — with an admin bypass on top:

1. **Instance ownership** — users can only see and manage the workshop
   instances they launched.
2. **Template access** — any authenticated user can read templates; only
   admins can create, edit, or delete them.
3. **Admin bypass** — users whose email is in `ORCHESTRA_ADMIN_EMAILS` can
   operate on any instance and manage templates.

## Instance ownership

Every workshop **instance** records the email of the user who launched it in
the `owner_email` column on the `workshop_instances` table. This value is:

- **Stamped at launch time** by the API from the authenticated user's email
  (`current_user.email`). Callers cannot set it themselves.
- **The basis for filtering** — `GET /instances/` filters rows by
  `WorkshopInstance.owner_email == current_user.email` (admins see all).
- **Reflected in responses** — `WorkshopInstanceResponse.owner_email` is the
  launcher's email.

Access checks happen in the DB layer, not via a Kubernetes label selector.
The Workshop CR the operator creates carries only the labels
`{app: orchestra-operator, managed-by: orchestra-api}` — there is **no**
owner label on the CR. The CR's `spec.owner` field exists (it is what the
per-pod sidecar enforces; see [Authentication](./authentication)), but
instance-list authorization is driven entirely by the `owner_email` DB column.

## Template ownership

Templates have **no owner**. They are shared catalog entries: the only
person-related column is `created_by`, the email of the admin who created the
template (`WorkshopTemplateResponse.created_by`). It is informational and does
**not** restrict access — every authenticated user can read every template.

## Route behaviour

Instances are addressed by their Kubernetes name (`{k8s_name}`); templates are
addressed by UUID (`{template_id}`).

### Instances — owner-or-admin, 404 on mismatch

| Operation | Regular user | Admin |
|---|---|---|
| `GET /instances/` | Lists only instances where `owner_email = self` | Lists all |
| `GET /instances/{k8s_name}` | 200 if owner matches, **404** otherwise | 200 always |
| `POST /instances/{k8s_name}/extend` | Extends if owner matches, **404** otherwise | Extends always |
| `DELETE /instances/{k8s_name}` | Terminates if owner matches, **404** otherwise | Terminates always |

Returning `404` (not `403`) for another user's instance prevents leaking
information about which instances exist. An attacker cannot distinguish "this
instance doesn't exist" from "this instance exists but belongs to someone else."

### Templates — read-any, write-admin (403)

| Operation | Regular user | Admin |
|---|---|---|
| `GET /templates/` | Lists active templates | Lists all (incl. inactive) |
| `GET /templates/{template_id}` | 200 | 200 |
| `POST /templates/{template_id}/launch` | Launches an instance owned by self | Same |
| `POST /templates/` | **403 Forbidden** | Creates the template |
| `PUT /templates/{template_id}` | **403 Forbidden** | Updates the template |
| `DELETE /templates/{template_id}` | **403 Forbidden** | Archives/deletes the template |

Template mutations are gated by the `require_admin` dependency, which returns
**403** (not 404) for non-admins — there is no existence to hide, since any
user may already read the template.

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

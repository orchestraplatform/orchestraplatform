# Workshop templates

Canonical, git-managed workshop templates (ADR-0006). Each `*.yaml` file in this
directory is one template the platform offers in its catalog.

These files are the **source of truth** — not the database. The Helm chart renders
them into a ConfigMap mounted into the API, which loads them into an in-memory
registry at startup. To change the catalog, edit a file here and open a PR; an
admin merges and a `helm upgrade` rolls it out.

## Adding or changing a template

1. Copy an existing file (e.g. `rstudio.yaml`) to `<slug>.yaml`.
2. Edit the fields. Your editor validates against `template.schema.json` via the
   `# yaml-language-server: $schema=` directive on the first line.
3. Open a PR. CI validates every file against the schema (`just validate-templates`).
4. An admin reviews and merges; the next deploy picks it up.

To retire a template without deleting its file, set `enabled: false`.

## Fields

See `template.schema.json` for the authoritative contract. Key fields:

| Field             | Required | Notes                                                        |
| ----------------- | -------- | ------------------------------------------------------------ |
| `name`            | yes      | Human-readable display name.                                 |
| `slug`            | yes      | k8s-safe id (lowercase, max 40); prefixes instance names.    |
| `image`           |          | Container image (default `rocker/rstudio:latest`).           |
| `port`            |          | App port inside the container (default `8787`).              |
| `tier`            |          | `small` or `large` tenant node pool (default `small`).       |
| `env` / `args`    |          | Extra env vars / CMD override.                               |
| `resources`       |          | cpu/memory limits + requests.                                |
| `storage`         |          | PVC size + storage class.                                    |
| `tags`            |          | Catalog filter tags.                                         |
| `enabled`         |          | `false` retires the template (default `true`).               |

## Regenerating the schema

`template.schema.json` is generated from the `WorkshopTemplateFile` model:

```sh
just template-schema
```

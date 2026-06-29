# orchestra-template-tools

Schema, validation, and CLI for Orchestra **workshop-template** YAML files
(ADR-0007). This package is the single source of truth for the template
contract, shared by three consumers:

- the platform API, which depends on this package for its models and runtime
  re-validation;
- the `orchestra-validate-templates` CLI, run by `just validate-templates`;
- the `workshop-templates` repo's CI, which installs this package from git
  (pinned to a platform tag) and runs the CLI on every PR.

It is deliberately dependency-light (pydantic + pyyaml) so a templates repo can
install it in CI without the platform's server/operator stack.

## CLI

```sh
# Validate a directory of template files
orchestra-validate-templates ./templates

# Emit the JSON Schema (what template.schema.json is generated from)
orchestra-validate-templates --print-schema > template.schema.json
```

## Library

```python
from orchestra_template_tools import validate_documents, build_schema

result = validate_documents({"rstudio.yaml": text})
if not result.ok:
    ...  # result.files[*].errors, result.errors
```

## Install from git (templates repo CI)

```sh
pip install "git+https://github.com/orchestraplatform/orchestraplatform.git@vX.Y.Z#subdirectory=template-tools"
```

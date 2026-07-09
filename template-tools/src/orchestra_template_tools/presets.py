"""Front-door workshop-size presets (ADR-0009).

``size`` is a **front-door input only** — the issue form offers four named
sizes, each bundling a tenant ``tier`` and a curated cpu/memory/ephemeral
profile aligned to what the node pools can schedule. Sizes are expanded to
explicit ``tier`` + ``resources`` before validation (see
:func:`orchestra_template_tools.render.render_submission`), so the generated
template YAML carries only concrete resources. ``size`` is never a stored
template field: the model and schema don't know it.

When the node pools change (ADR-0005), these presets are part of that change's
blast radius — they encode pool capacity in one reviewable place.
"""


# Field names are WorkshopResources aliases (camelCase): cpu/memory/
# ephemeralStorage are limits, *Request are the requests.
def _resources(memory: str) -> dict[str, str]:
    return {
        "cpu": "2",
        "cpuRequest": "500m",
        "memory": memory,
        "memoryRequest": memory,
        "ephemeralStorage": "8Gi",
        "ephemeralStorageRequest": "8Gi",
    }


SIZE_PRESETS: dict[str, dict[str, object]] = {
    "small": {"tier": "small", "resources": _resources("2Gi")},
    "standard": {"tier": "small", "resources": _resources("4Gi")},
    "large": {"tier": "large", "resources": _resources("8Gi")},
    "xlarge": {"tier": "large", "resources": _resources("16Gi")},
}

# Preset keys, in form/menu order.
SIZE_NAMES: tuple[str, ...] = tuple(SIZE_PRESETS)

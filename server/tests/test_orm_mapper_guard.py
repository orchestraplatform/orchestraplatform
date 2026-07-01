"""ORM integrity guard — configure mappers and resolve every ForeignKey.

Mocked-DB unit tests never touch a real schema, so an ORM regression can pass
the whole suite yet 500 on every request against real Postgres. This actually
happened: ``WorkshopInstance.workshop_id`` carried a ``ForeignKey`` to a
``workshops`` table that had been dropped (ADR-0006 phase 6). Every launch
crashed; no mocked test noticed.

These tests are pure in-memory metadata checks (no DB connection):

* ``configure_mappers()`` forces SQLAlchemy to resolve every relationship and
  raises if any mapper is misconfigured.
* We then walk ``Base.metadata`` and assert every ``ForeignKey`` points at a
  table + column that actually exists in the mapped metadata.
"""

import importlib
import pkgutil

import pytest
from sqlalchemy.orm import configure_mappers

import api.models.db as db_models
from api.core.database import Base


def _import_all_models() -> None:
    """Import every module under ``api.models.db`` so all mappers register.

    ``api.models.db.__init__`` already imports the known models, but importing
    the whole package defends against a new model module that someone forgets to
    re-export there.
    """
    importlib.import_module("api.models.db")
    for mod in pkgutil.iter_modules(db_models.__path__):
        importlib.import_module(f"{db_models.__name__}.{mod.name}")


def test_configure_mappers_succeeds():
    """All ORM relationships resolve — catches broken back_populates / typos."""
    _import_all_models()
    configure_mappers()


def test_every_foreign_key_target_exists():
    """Every ForeignKey resolves to a table + column present in the metadata.

    A dangling FK (target table dropped/renamed) is exactly the regression that
    slipped past the mocked-DB suite and 500'd every launch on real Postgres.
    """
    _import_all_models()
    configure_mappers()

    metadata = Base.metadata
    tables = metadata.tables
    dangling: list[str] = []

    for table in tables.values():
        for fk in table.foreign_keys:
            target_table = fk.column.table.key
            target_col = fk.column.name
            if target_table not in tables:
                dangling.append(
                    f"{table.name}.{fk.parent.name} -> missing table '{target_table}'"
                )
            elif target_col not in tables[target_table].columns:
                dangling.append(
                    f"{table.name}.{fk.parent.name} -> "
                    f"'{target_table}.{target_col}' (column missing)"
                )

    assert not dangling, "dangling foreign key(s):\n  " + "\n  ".join(dangling)


def test_mapped_models_are_registered():
    """Sanity: the guard actually has models to check (not silently empty)."""
    _import_all_models()
    configure_mappers()
    mapped = [m.class_.__name__ for m in Base.registry.mappers]
    assert mapped, "no ORM models registered — guard would be a no-op"


@pytest.mark.parametrize("table_name", ["workshop_instances", "instance_events"])
def test_known_tables_present(table_name: str):
    """The two ADR-0006 tables must stay mapped."""
    _import_all_models()
    assert table_name in Base.metadata.tables


def test_no_reference_to_dropped_workshops_table():
    """Regression pin: the dropped ``workshops`` table must not resurface as a
    ForeignKey target (the original dangling-FK bug, ADR-0006 phase 6)."""
    _import_all_models()
    for table in Base.metadata.tables.values():
        for fk in table.foreign_keys:
            assert fk.column.table.key != "workshops", (
                f"{table.name}.{fk.parent.name} references the dropped "
                "'workshops' table — see ADR-0006 phase 6"
            )

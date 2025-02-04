"""Strict configuration schema tests."""

from __future__ import annotations

import pytest

import frugent.config as cfg


def test_default_runtime_config_has_bounded_offline_limits() -> None:
    config = cfg.RuntimeConfig()
    assert config.max_steps == 8
    assert config.token_budget == 4096
    assert config.cost_budget_micros == 100_000
    assert config.schema_version == cfg.CURRENT_SCHEMA_VERSION


@pytest.mark.parametrize(
    "kwargs",
    [
        {"seed": -1},
        {"max_steps": 0},
        {"token_budget": 0},
        {"cost_budget_micros": -1},
        {"quality_floor": -0.01},
        {"quality_floor": 1.01},
    ],
)
def test_runtime_config_rejects_impossible_limits(kwargs: dict[str, object]) -> None:
    with pytest.raises(cfg.ConfigError, match="config"):
        cfg.RuntimeConfig(**kwargs)


def test_config_record_roundtrip_is_exact() -> None:
    original = cfg.RuntimeConfig(seed=17, max_steps=3, token_budget=700, quality_floor=0.75)
    assert cfg.RuntimeConfig.from_record(original.to_record()) == original


@pytest.mark.parametrize(
    ("mutation", "fragment"),
    [
        ({"remove": "seed"}, r"missing=\['seed'\]"),
        ({"extra": ("endpoint", "https://invalid")}, r"unknown=\['endpoint'\]"),
    ],
)
def test_config_record_rejects_schema_drift(mutation: dict[str, object], fragment: str) -> None:
    record = cfg.RuntimeConfig().to_record()
    if "remove" in mutation:
        record.pop(str(mutation["remove"]))
    else:
        key, value = mutation["extra"]  # type: ignore[misc]
        record[key] = value  # type: ignore[index]
    with pytest.raises(cfg.ConfigError, match=fragment):
        cfg.RuntimeConfig.from_record(record)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"seed": True},
        {"max_steps": 1.5},
        {"token_budget": "4096"},
        {"cost_budget_micros": False},
        {"schema_version": 1},
        {"quality_floor": float("nan")},
    ],
)
def test_runtime_config_does_not_coerce_deceptive_scalars(kwargs: dict[str, object]) -> None:
    with pytest.raises((cfg.ConfigError, TypeError), match="config"):
        cfg.RuntimeConfig(**kwargs)


def test_v1_config_migration_renames_limits_and_adds_quality_floor() -> None:
    migrated = cfg.migrate_config(
        {"schema_version": 1, "seed": 2, "steps": 4, "tokens": 900, "cost_micros": 50_000}
    )
    assert migrated == {
        "schema_version": 2,
        "seed": 2,
        "max_steps": 4,
        "token_budget": 900,
        "cost_budget_micros": 50_000,
        "quality_floor": 0.8,
    }


def test_current_config_migration_is_idempotent() -> None:
    record = cfg.RuntimeConfig(seed=3).to_record()
    assert cfg.migrate_config(cfg.migrate_config(record)) == record


@pytest.mark.parametrize("version", [None, 0, -1, 3, "1", True])
def test_config_migration_rejects_unknown_versions(version: object) -> None:
    with pytest.raises(cfg.ConfigError, match="unsupported schema_version"):
        cfg.migrate_config({"schema_version": version})


def test_v1_migration_rejects_undeclared_fields() -> None:
    legacy = {
        "schema_version": 1,
        "seed": 0,
        "steps": 2,
        "tokens": 10,
        "cost_micros": 20,
        "endpoint": "forbidden",
    }
    with pytest.raises(cfg.ConfigError, match="unexpected fields"):
        cfg.migrate_config(legacy)


def test_config_fingerprint_changes_with_effective_limit() -> None:
    base = cfg.RuntimeConfig(seed=5, token_budget=100)
    changed = cfg.RuntimeConfig(seed=5, token_budget=101)
    assert base.fingerprint != changed.fingerprint
    assert base.fingerprint == cfg.RuntimeConfig(seed=5, token_budget=100).fingerprint


def test_dump_config_is_canonical_and_newline_terminated() -> None:
    dumped = cfg.dump_config(cfg.RuntimeConfig(seed=9))
    assert dumped.endswith(b"\n")
    assert b" " not in dumped
    assert dumped.startswith(b'{"cost_budget_micros":')


def test_load_config_inverts_dump_config() -> None:
    original = cfg.RuntimeConfig(seed=12, max_steps=5, quality_floor=0.91)
    assert cfg.load_config(cfg.dump_config(original)) == original


def test_load_config_applies_supported_migration() -> None:
    legacy = b'{"cost_micros":90,"schema_version":1,"seed":3,"steps":2,"tokens":40}'
    loaded = cfg.load_config(legacy)
    assert loaded.schema_version == cfg.CURRENT_SCHEMA_VERSION
    assert loaded.token_budget == 40


@pytest.mark.parametrize("payload", [b"[]", b"null", b"not json"])
def test_load_config_rejects_non_object_documents(payload: bytes) -> None:
    with pytest.raises(cfg.ConfigError, match="config JSON"):
        cfg.load_config(payload)

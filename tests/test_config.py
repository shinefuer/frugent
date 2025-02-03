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
        ({"remove": "seed"}, "missing=\['seed'\]"),
        ({"extra": ("endpoint", "https://invalid")}, "unknown=\['endpoint'\]"),
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

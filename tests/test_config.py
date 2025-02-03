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

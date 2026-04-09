"""Golden public facade and import behavior."""

from __future__ import annotations

import frugent


def test_configuration_facade_roundtrips_without_private_imports() -> None:
    config = frugent.RuntimeConfig(seed=4)
    assert frugent.load_config(frugent.dump_config(config)) == config
    assert issubclass(frugent.ConfigError, ValueError)

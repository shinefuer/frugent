"""Golden public facade and import behavior."""

from __future__ import annotations

import frugent


def test_configuration_facade_roundtrips_without_private_imports() -> None:
    config = frugent.RuntimeConfig(seed=4)
    assert frugent.load_config(frugent.dump_config(config)) == config
    assert issubclass(frugent.ConfigError, ValueError)


def test_rate_card_facade_is_explicitly_fictional() -> None:
    card = frugent.demo_rate_card()
    assert "fictional" in card.label
    assert frugent.rate_card_fingerprint(card).startswith("sha256:")


def test_record_types_are_available_from_one_namespace() -> None:
    message = frugent.Message("user", "hello")
    request = frugent.Request("r", (message,), 2)
    assert request.messages == (message,)
    assert frugent.Usage(2, 1).total_tokens == 3

"""Deterministic tokenizer and prompt accounting tests."""

from __future__ import annotations

import pytest

import frugent.tokenizer as tok


def test_heuristic_tokenizer_separates_words_numbers_and_punctuation() -> None:
    tokenizer = tok.HeuristicTokenizer()
    assert tokenizer.encode("fix item_2: cost=17!") == (
        "fix",
        "item_2",
        ":",
        "cost",
        "=",
        "17",
        "!",
    )
    assert tokenizer.count("fix item_2: cost=17!") == 7


def test_lowercase_mode_uses_unicode_casefold() -> None:
    assert tok.HeuristicTokenizer(lowercase=True).encode("Straße HTTP") == ("strasse", "http")


@pytest.mark.parametrize("seed", [-1, True, 1.5, "1"])
def test_tokenizer_rejects_ambiguous_seed(seed: object) -> None:
    with pytest.raises(tok.TokenizerError, match="seed"):
        tok.HeuristicTokenizer(seed=seed)  # type: ignore[arg-type]

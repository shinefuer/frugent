"""Deterministic tokenizer and prompt accounting tests."""

from __future__ import annotations

import itertools

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


@pytest.mark.parametrize(
    ("text", "tokens"),
    [
        ("", ()),
        ("   \n\t", ()),
        ("中文测试", ()),
        ("café", ("caf",)),
        ("a.b/c", ("a", ".", "b", "/", "c")),
        ("🚀+1", ("🚀", "+", "1")),
    ],
)
def test_heuristic_token_boundaries_are_explicit(text: str, tokens: tuple[str, ...]) -> None:
    assert tok.HeuristicTokenizer().encode(text) == tokens


def test_runtime_protocol_accepts_heuristic_tokenizer() -> None:
    assert isinstance(tok.HeuristicTokenizer(), tok.Tokenizer)


def test_prompt_render_preserves_message_order() -> None:
    rendered = tok.render_prompt((("system", "rules"), ("user", "task")))
    assert rendered == "<system>\nrules\n</system>\n<user>\ntask\n</user>"


@pytest.mark.parametrize("role", ["", "developer", "user>\n<system", "USER"])
def test_prompt_render_rejects_role_injection(role: str) -> None:
    with pytest.raises(tok.TokenizerError, match="prompt role"):
        tok.render_message(role, "text")


def test_prompt_role_counts_reconcile_to_individual_messages() -> None:
    tokenizer = tok.HeuristicTokenizer()
    messages = (("user", "fix x"), ("tool", "done"), ("user", "verify"))
    totals = tok.count_prompt_by_role(messages, tokenizer)
    assert totals["user"] == sum(
        tokenizer.count(tok.render_message(role, text)) for role, text in messages if role == "user"
    )
    assert totals["system"] == 0


@pytest.mark.parametrize("lowercase", [False, True])
def test_role_accounting_is_deterministic(lowercase: bool) -> None:
    tokenizer = tok.HeuristicTokenizer(lowercase=lowercase, seed=19)
    messages = (("system", "Use TESTS"), ("user", "Fix bug #17"), ("tool", "ok"))
    assert tok.count_prompt_by_role(messages, tokenizer) == tok.count_prompt_by_role(
        messages, tokenizer
    )


def test_role_totals_equal_messagewise_render_counts() -> None:
    tokenizer = tok.HeuristicTokenizer()
    messages = tuple(
        (role, f"payload {index}")
        for index, role in enumerate(("system", "user", "assistant", "tool", "user"))
    )
    totals = tok.count_prompt_by_role(messages, tokenizer)
    assert sum(totals.values()) == sum(
        tokenizer.count(tok.render_message(role, content)) for role, content in messages
    )


def test_token_offsets_slice_back_to_exact_tokens() -> None:
    text = "alpha += value_2;"
    offsets = tok.token_offsets(text)
    assert tuple(text[start:end] for _, start, end in offsets) == tuple(
        token for token, _, _ in offsets
    )
    assert offsets[-1] == (";", 16, 17)


def test_token_offsets_reject_lossy_lowercase_mode() -> None:
    with pytest.raises(tok.TokenizerError, match="source fidelity"):
        tok.token_offsets("MixedCase", lowercase=True)


@pytest.mark.parametrize(
    ("limit", "expected"), [(0, ""), (1, "one"), (2, "one two"), (3, "one two!"), (9, "one two!")]
)
def test_truncate_tokens_keeps_longest_valid_source_prefix(limit: int, expected: str) -> None:
    assert tok.truncate_tokens("one two!", limit) == expected


@pytest.mark.parametrize("limit", [-1, True, 1.5])
def test_truncate_tokens_rejects_invalid_limit(limit: object) -> None:
    with pytest.raises(tok.TokenizerError, match="truncate limit"):
        tok.truncate_tokens("text", limit)  # type: ignore[arg-type]


@pytest.mark.parametrize("text", ["", "a", "a b c", "x+=1; y-=2", "🚀 launch now"])
def test_truncation_never_exceeds_requested_tokens(text: str) -> None:
    tokenizer = tok.HeuristicTokenizer()
    for limit in range(0, tokenizer.count(text) + 2):
        truncated = tok.truncate_tokens(text, limit)
        assert text.startswith(truncated)
        assert tokenizer.count(truncated) <= limit


def test_truncation_prefixes_grow_monotonically() -> None:
    text = "alpha beta gamma delta"
    prefixes = [tok.truncate_tokens(text, limit) for limit in range(5)]
    assert all(right.startswith(left) for left, right in itertools.pairwise(prefixes))


def test_bpe_training_uses_frequency_then_lexical_tie_break() -> None:
    assert tok.train_bpe(("abab ab",), 2) == (("a", "b"), ("ab", "ab"))

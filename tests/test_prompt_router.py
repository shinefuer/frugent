"""Behavior and invariant tests."""

from __future__ import annotations

import pytest

import frugent.prompt_router as m


def test_instance_keeps_explicit_queue_load() -> None:
    instance = m.Instance("worker-a", m.PrefixTrie(), 17)
    assert instance.name == "worker-a"
    assert instance.queued_tokens == 17


@pytest.mark.parametrize("values", [("", 0), ("a", -1)])
def test_instance_rejects_invalid_identity_or_queue(values: tuple[object, int]) -> None:
    with pytest.raises(m.PromptRouterError, match="router instance"):
        m.Instance(values[0], m.PrefixTrie(), values[1])  # type: ignore[arg-type]


def test_choose_instance_prefers_longest_cached_prefix() -> None:
    left, right = m.Instance("left", m.PrefixTrie()), m.Instance("right", m.PrefixTrie())
    left.cache.insert(("a",))
    right.cache.insert(("a", "b"))
    assert m.choose_instance((left, right), ("a", "b", "c")).name == "right"


def test_choose_instance_uses_stable_name_tie_break() -> None:
    assert (
        m.choose_instance(
            (m.Instance("z", m.PrefixTrie()), m.Instance("a", m.PrefixTrie())), ("x",)
        ).name
        == "a"
    )


def test_load_penalty_can_move_only_low_affinity_work() -> None:
    high = m.Instance("high", m.PrefixTrie(), queued_tokens=100)
    idle = m.Instance("idle", m.PrefixTrie(), queued_tokens=0)
    high.cache.insert(("a", "b", "c"))
    idle.cache.insert(("a",))
    assert m.choose_instance((high, idle), ("a", "b", "c"), load_penalty_ppm=1_000).name == "high"
    assert m.choose_instance((high, idle), ("a",), load_penalty_ppm=20_000).name == "idle"


def test_route_and_record_makes_followup_affine() -> None:
    instances = (m.Instance("a", m.PrefixTrie()), m.Instance("b", m.PrefixTrie()))
    assert m.route_and_record(instances, ("prefix", "task")) == "a"
    assert m.choose_instance(instances, ("prefix", "task", "next")).name == "a"
    assert instances[0].cache.sequence_count == 1


def test_route_trace_clusters_repeated_prefixes() -> None:
    requests = (("sys-a", "one"), ("sys-b", "one"), ("sys-a", "two"), ("sys-b", "two"))
    routed = m.route_trace(("a", "b"), requests)
    assert routed == ("a", "a", "a", "a")
    # With no planted initial placement the stable tie puts first misses on a;
    # later tests seed pools to compare cross-instance affinity.


def test_seeded_pool_routes_each_planted_prefix() -> None:
    instances = m.seeded_instances({"a": (("alpha", "rules"),), "b": (("beta", "rules"),)})
    assert m.choose_instance(instances, ("alpha", "rules", "task")).name == "a"
    assert m.choose_instance(instances, ("beta", "rules", "task")).name == "b"


@pytest.mark.parametrize("length", range(0, 12))
def test_routed_hits_never_exceed_request_tokens(length: int) -> None:
    instance = m.seeded_instances({"a": (tuple(str(index) for index in range(20)),)})
    request = tuple(str(index) for index in range(length))
    assert 0 <= instance[0].cache.longest_prefix(request) <= length


def test_routed_hit_tokens_sum_fixed_snapshot_matches() -> None:
    instances = m.seeded_instances({"a": (("x", "a"),), "b": (("x", "b"),)})
    requests = (("x", "a", "1"), ("x", "b", "2"))
    assert m.routed_hit_tokens(instances, ("a", "b"), requests) == 4
    assert m.routed_hit_tokens(instances, ("b", "a"), requests) == 2


def test_exhaustive_assignment_recovers_planted_optimum() -> None:
    instances = m.seeded_instances({"a": (("alpha", "rules"),), "b": (("beta", "rules"),)})
    requests = (("alpha", "rules", "1"), ("beta", "rules", "2"), ("alpha", "rules", "3"))
    optimum = m.exhaustive_assignment(instances, requests)
    assert optimum == ("a", "b", "a")
    assert m.routed_hit_tokens(instances, optimum, requests) == 6


@pytest.mark.parametrize("seed", range(8))
def test_exhaustive_router_recovers_planted_hits(seed: int) -> None:
    prefixes = {"a": ((str(seed), "a"),), "b": ((str(seed), "b"),)}
    instances = m.seeded_instances(prefixes)
    requests = ((str(seed), "a", "x"), (str(seed), "b", "y"), ("miss", str(seed)))
    optimum = m.exhaustive_assignment(instances, requests)
    assert m.routed_hit_tokens(instances, optimum, requests) == 4


def test_greedy_fixed_router_matches_separable_optimum() -> None:
    instances = m.seeded_instances({"a": (("a", "x"),), "b": (("b", "x"),)})
    requests = (("a", "x", "1"), ("b", "x", "2"), ("none",))
    assert m.greedy_fixed_assignment(instances, requests) == m.exhaustive_assignment(
        instances, requests
    )
    assert m.optimum_ratio(instances, requests) == 1.0


def test_greedy_fixed_routing_matches_exhaustive_independent_choices() -> None:
    import itertools

    placements = {"a": (("x", "a"), ("shared",)), "b": (("x", "b"),), "c": (("z",),)}
    instances = m.seeded_instances(placements)
    alphabet = ("x", "z", "shared")
    requests = tuple((head, tail) for head, tail in itertools.product(alphabet, ("a", "b")))
    greedy = m.greedy_fixed_assignment(instances, requests)
    optimum = m.exhaustive_assignment(instances, requests)
    assert m.routed_hit_tokens(instances, greedy, requests) == m.routed_hit_tokens(
        instances, optimum, requests
    )
    assert m.optimum_ratio(instances, requests) == 1.0

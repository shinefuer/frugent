"""Public facade for deterministic cost-efficient runtime mechanics."""

from frugent._version import __version__
from frugent.batching import BatchRequest, execute_single_flights, micro_batches
from frugent.compression import Block, exact_budget_select, recall_curve, sliding_window
from frugent.config import ConfigError, RuntimeConfig, dump_config, load_config, migrate_config
from frugent.context import (
    ContextDiff,
    MessageStore,
    Snapshot,
    apply_diff,
    diff,
    snapshot,
    store_fingerprint,
)
from frugent.prompt_cache import CacheEntry, CacheMetrics, CachePolicy, replay_trace
from frugent.ratecard import (
    CostBreakdown,
    ModelRate,
    RateCard,
    RateCardError,
    demo_rate_card,
    price_usage,
    rate_card_fingerprint,
)
from frugent.semantic_cache import (
    SemanticEntry,
    SemanticMetrics,
    exact_key,
    exact_lookup,
    fuzzy_candidates,
)
from frugent.types import Decision, Event, Message, RecordError, Request, Response, Usage

__all__ = [
    "BatchRequest",
    "Block",
    "CacheEntry",
    "CacheMetrics",
    "CachePolicy",
    "ConfigError",
    "ContextDiff",
    "CostBreakdown",
    "Decision",
    "Event",
    "Message",
    "MessageStore",
    "ModelRate",
    "RateCard",
    "RateCardError",
    "RecordError",
    "Request",
    "Response",
    "RuntimeConfig",
    "SemanticEntry",
    "SemanticMetrics",
    "Snapshot",
    "Usage",
    "__version__",
    "apply_diff",
    "demo_rate_card",
    "diff",
    "dump_config",
    "exact_budget_select",
    "exact_key",
    "exact_lookup",
    "execute_single_flights",
    "fuzzy_candidates",
    "load_config",
    "micro_batches",
    "migrate_config",
    "price_usage",
    "rate_card_fingerprint",
    "recall_curve",
    "replay_trace",
    "sliding_window",
    "snapshot",
    "store_fingerprint",
]

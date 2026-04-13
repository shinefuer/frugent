"""Public facade for deterministic cost-efficient runtime mechanics."""

from frugent._version import __version__
from frugent.batching import BatchRequest, execute_single_flights, micro_batches
from frugent.budget import Budget, BudgetError, can_admit, reserve
from frugent.cascade import ModelProfile, cheapest_profile_at_floor
from frugent.cascade_dp import DifficultyMixture, Policy, optimal_policy, optimum_gap
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
from frugent.scheduling import Task as ScheduledTask
from frugent.scheduling import schedule
from frugent.semantic_cache import (
    SemanticEntry,
    SemanticMetrics,
    exact_key,
    exact_lookup,
    fuzzy_candidates,
)
from frugent.trace_io import TraceHeader, event_diff, export_trace, import_trace, trace_fingerprint
from frugent.tracing import Span, span_diff
from frugent.types import Decision, Event, Message, RecordError, Request, Response, Usage

__all__ = [
    "BatchRequest",
    "Block",
    "Budget",
    "BudgetError",
    "CacheEntry",
    "CacheMetrics",
    "CachePolicy",
    "ConfigError",
    "ContextDiff",
    "CostBreakdown",
    "Decision",
    "DifficultyMixture",
    "Event",
    "Message",
    "MessageStore",
    "ModelProfile",
    "ModelRate",
    "Policy",
    "RateCard",
    "RateCardError",
    "RecordError",
    "Request",
    "Response",
    "RuntimeConfig",
    "ScheduledTask",
    "SemanticEntry",
    "SemanticMetrics",
    "Snapshot",
    "Span",
    "TraceHeader",
    "Usage",
    "__version__",
    "apply_diff",
    "can_admit",
    "cheapest_profile_at_floor",
    "demo_rate_card",
    "diff",
    "dump_config",
    "event_diff",
    "exact_budget_select",
    "exact_key",
    "exact_lookup",
    "execute_single_flights",
    "export_trace",
    "fuzzy_candidates",
    "import_trace",
    "load_config",
    "micro_batches",
    "migrate_config",
    "optimal_policy",
    "optimum_gap",
    "price_usage",
    "rate_card_fingerprint",
    "recall_curve",
    "replay_trace",
    "reserve",
    "schedule",
    "sliding_window",
    "snapshot",
    "span_diff",
    "store_fingerprint",
    "trace_fingerprint",
]

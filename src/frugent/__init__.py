"""Public facade for deterministic cost-efficient runtime mechanics."""

from frugent._version import __version__
from frugent.adapters import (
    Adapter,
    AdapterRequest,
    AdapterResponse,
    ReplayAdapter,
    ScriptedAdapter,
)
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
from frugent.runtime import Action, LoopEvent, ScriptedPlanner, run_loop
from frugent.sandbox import Decision as SandboxDecision
from frugent.sandbox import Policy as SandboxPolicy
from frugent.sandbox import decide
from frugent.scheduling import Task as ScheduledTask
from frugent.scheduling import schedule
from frugent.semantic_cache import (
    SemanticEntry,
    SemanticMetrics,
    exact_key,
    exact_lookup,
    fuzzy_candidates,
)
from frugent.tools import ScriptedTools, ToolCall, ToolResult, dry_run, execute
from frugent.trace_io import TraceHeader, event_diff, export_trace, import_trace, trace_fingerprint
from frugent.tracing import Span, span_diff
from frugent.types import Decision, Event, Message, RecordError, Request, Response, Usage

__all__ = [
    "Action",
    "Adapter",
    "AdapterRequest",
    "AdapterResponse",
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
    "LoopEvent",
    "Message",
    "MessageStore",
    "ModelProfile",
    "ModelRate",
    "Policy",
    "RateCard",
    "RateCardError",
    "RecordError",
    "ReplayAdapter",
    "Request",
    "Response",
    "RuntimeConfig",
    "SandboxDecision",
    "SandboxPolicy",
    "ScheduledTask",
    "ScriptedAdapter",
    "ScriptedPlanner",
    "ScriptedTools",
    "SemanticEntry",
    "SemanticMetrics",
    "Snapshot",
    "Span",
    "ToolCall",
    "ToolResult",
    "TraceHeader",
    "Usage",
    "__version__",
    "apply_diff",
    "can_admit",
    "cheapest_profile_at_floor",
    "decide",
    "demo_rate_card",
    "diff",
    "dry_run",
    "dump_config",
    "event_diff",
    "exact_budget_select",
    "exact_key",
    "exact_lookup",
    "execute",
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
    "run_loop",
    "schedule",
    "sliding_window",
    "snapshot",
    "span_diff",
    "store_fingerprint",
    "trace_fingerprint",
]

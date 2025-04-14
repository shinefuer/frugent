# Hard budgets

预算同时约束 token 与整数微单位成本。`reserve` 是 immutable、全有或全无的操作；任何已接受路径都不会越过限制。降级顺序固定为 full → downgrade → compress → cache_only → defer，并总是选择第一个可承受阶段。

`partition` 用整数除法分配 remaining resources，再按稳定索引分发余数，因此子预算之和精确守恒。

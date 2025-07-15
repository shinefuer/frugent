# Batching and single flight

equivalence key 覆盖原始 payload bytes。single flight 每个 exact key 只执行一次，再把同一 bytes response 分发给所有 subscriber；不同 payload 永不合并。

micro-batch 同时受首个 arrival 的 window 与 max size 约束。latency 是确定性队列模拟值，不是实际网络测量。

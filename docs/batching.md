# Batching and single flight

equivalence key 覆盖原始 payload bytes。single flight 每个 exact key 只执行一次，再把同一 bytes response 分发给所有 subscriber；不同 payload 永不合并。

micro-batch 同时受首个 arrival 的 window 与 max size 约束。满 batch 在最后一个成员到达时 dispatch；未满 batch 在首个成员的 deadline dispatch。`scheduled_completion_times` 再叠加串行 service queue，因此每个 subscriber 的 completion time 可由同一 arrival trace 精确重放。latency 是确定性队列模拟值，不是实际网络测量。

# Benchmark assumptions

No-cache、no-batching、single-premium 与 unlimited-budget baselines 使用同一 ordered synthetic task list。FIFO latency 从 integer arrival/service events 推导；P50/P95 不读取 wall clock。

Token savings 以 baseline prompt tokens 为 denominator；cache uplift 是相同请求数下的 absolute hit-rate difference；cost per completion 使用 fictional integer total。bootstrap CI 对 task-aligned delta seeded resampling。

该模型用于发现机制回归，不估计硬件吞吐、provider queue 或真实回答质量。

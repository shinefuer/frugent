# Limitations

- Heuristic tokenizer 不等同于服务端 tokenizer。
- Cache 只模拟逻辑 lifecycle，不存储真实 KV tensors。
- Semantic fuzzy key 只用于 candidate discovery；retrieval 仍要求 exact equivalence。
- Simulated latency 不包含网络、GPU、编译或 provider queue。
- Scripted success、planted optimum 与 fictional rate card 只验证约束求解。
- Sandbox allowlist 不替代 OS/container isolation。
- Loopback adapter 不测试公网、认证、配额或真实 endpoint compatibility。

因此报告适合机制回归，不适合采购决策、真实模型排名或 production SLO 预测。

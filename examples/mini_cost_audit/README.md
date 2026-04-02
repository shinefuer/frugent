# Full mini cost audit

运行 `python examples/mini_cost_audit/example.py result.html`。脚本实际执行 seeded workload synthesis、baseline 与 stack accounting、checksummed trace 和 self-contained HTML report，stdout 只摘要本次 synthetic measurement。

报告中的 token、cost 与 simulated latency 均来自此次执行；rate card 明确为 fictional，limitations 明确说明未调用真实端点、未使用外部数据集、未评测模型回答质量。

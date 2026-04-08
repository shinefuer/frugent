# Offline examples

- `prompt_cache_routing`：planted prefix affinity 与 token SVG。
- `cascade_optimum`：scripted difficulty mixture、quality floor 与最优 policy。
- `compression_recall`：planted needle recall 随 token budget 的曲线。
- `mini_cost_audit`：从 workload 到 HTML report 的完整离线审计。

所有脚本均接受首个位置参数作为输出文件；未提供时写入当前目录。它们不需要网络、密钥、GPU、预训练权重或外部数据集。

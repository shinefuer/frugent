# frugent

frugent 是一个 Python 3.11+ 工具包，用于在完全离线、可复现的合成编码工作负载上验证成本高效 agent 运行时机制。项目聚焦路由、缓存、压缩、批处理、预算、追踪和沙箱执行的工程行为，不评估任何真实大模型的质量。

默认测试不访问网络、不需要 API key、GPU、预训练权重或外部数据集。报告中的成本使用明确标注的 fictional rate card；合成任务包含 planted solution path 与已知最优成本，用来验证机制而非代表生产负载。

## 机制范围

| 机制 | 可验证行为 |
|---|---|
| prefix / semantic cache | affinity routing、TTL、LRU/LFU、严格 exact retrieval |
| context compression | sliding window、extractive scoring、knapsack、needle recall |
| batching | single-flight、fan-out、micro-batch wait bound |
| cascade / budget | quality floor、DP optimum、hard admission、degradation ladder |
| tracing / sandbox | cost conservation、checksummed JSONL、allowlist、timeout/replay |
| offline runtime | scripted/replay/local-loopback adapter、plan→act→observe |

这些机制验证“如何运行与计量”，不验证真实 LLM 回答质量。

## 开发

```bash
uv venv .venv
uv pip install --python .venv/bin/python -e ".[dev]"
make build test format-check
```

## 时间线说明

本项目于 2026 年 10 月创建和验证。Git 中 2025 年至 2026 年 10 月的日期是本次生成的演示时间线，不代表那些日期已经开展的工作。每次开发提交均执行构建、测试与格式检查；未使用空提交。项目未宣称论文成果、预训练模型或真实模型服务/生产负载成绩。

## 许可

MIT License，详见 [LICENSE](LICENSE)。


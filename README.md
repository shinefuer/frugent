# frugent

frugent 是一个 Python 3.11+ 工具包，用于在完全离线、可复现的合成编码工作负载上验证成本高效 agent 运行时机制。项目聚焦路由、缓存、压缩、批处理、预算、追踪和沙箱执行的工程行为，不评估任何真实大模型的质量。

默认测试不访问网络、不需要 API key、GPU、预训练权重或外部数据集。报告中的成本使用明确标注的 fictional rate card；合成任务包含 planted solution path 与已知最优成本，用来验证机制而非代表生产负载。

## 机制范围

| 机制 | 可验证行为 |
|---|---|
| prefix / semantic cache | affinity routing、TTL、LRU/LFU、严格 exact retrieval |
| context compression | sliding window、extractive scoring、knapsack、needle recall |
| batching | single-flight、fan-out、deadline dispatch、micro-batch wait bound |
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

可选 CPU PyTorch demo：

```bash
uv pip install --python .venv/bin/python --extra-index-url https://download.pytorch.org/whl/cpu --index-strategy unsafe-best-match -e ".[dev,torch]"
make test-all typecheck
```

默认 NumPy 路径不加载 torch；`uv.lock` 固定开发解析结果。

## 快速使用

```bash
frugent route
frugent compress --token-budget 4096
frugent bench --seed 7 --tasks 24
frugent report --seed 7 --tasks 24 --format html --output report.html
frugent demo --seed 7 --tasks 12
```

机制命令输出 canonical JSON；`run` / `demo` 同时给出实际 route/cache/batch/budget stage 计数，`report` 直接输出 Markdown/HTML。cost 是 fictional micro-cost，latency 是离散事件模拟值。

## 示例

- [prompt-cache routing](examples/prompt_cache_routing/README.md)：planted affinity 与 SVG。
- [cascade optimum](examples/cascade_optimum/README.md)：runtime policy 与 DP optimum。
- [compression recall](examples/compression_recall/README.md)：token budget degradation curve。
- [mini cost audit](examples/mini_cost_audit/README.md)：完整 HTML 成本报告。

四个示例均执行项目函数得到输出，不依赖预先写好的结果表。

## 证据边界

- token savings、cache hit、cost、latency、recall 只来自 seeded synthetic workload。
- fictional rate card 不映射任何服务商价格；scripted success 不代表真实模型 accuracy。
- local loopback HTTP 测试只连接测试进程；默认路径不发送网络请求。
- optional training 只拟合 planted binary labels，并验证 deterministic loss decrease。

完整口径见 [evaluation](docs/evaluation.md) 与 [limitations](docs/limitations.md)。

## 许可

MIT License，详见 [LICENSE](LICENSE)。

# Offline pipeline

`run_pipeline` 以同一个 seed 生成 planted coding tasks，分别执行 no-optimization baseline 与 prefix route → prompt cache → micro-batch → hard budget stack 的实际计数逻辑，再从这些计数生成 checksummed trace、Markdown 和 self-contained HTML。

`TaskMeasurement` 保存每个任务的 prompt/completion/cache token、fictional micro-cost 与 simulated latency。预算按 seeded task order 原子准入：不适配的任务被跳过，已准入集合的 token 与 cost 总和始终不越界。`StackStages` 汇总 routed prefix tokens、cache hits、batch/execution 数和 admission 数；报告中的 mechanics 段和 trace stage event 都来自这份执行结果。

所有价格来自项目内的 fictional rate card；latency 是文档化的离散事件模拟值。pipeline 不连接真实端点，也不把 scripted completion 当作模型质量。

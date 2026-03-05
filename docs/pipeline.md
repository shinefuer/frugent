# Offline pipeline

`run_pipeline` 以同一个 seed 生成 planted coding tasks，分别执行 no-optimization baseline 与 cache/batch/budget stack 的实际计数逻辑，再从这些计数生成 checksummed trace、Markdown 和 self-contained HTML。

所有价格来自项目内的 fictional rate card；latency 是文档化的离散事件模拟值。pipeline 不连接真实端点，也不把 scripted completion 当作模型质量。

# Architecture

数据流为 `RuntimeConfig → workload → tokenizer/context → route/cache/compress/batch → cascade/budget → adapter/tool loop → trace/attribution → benchmark/report`。各层只交换 frozen dataclass、tuple、bytes 或 versioned record。

`pipeline` 是组合层：baseline 与 stack 共享 task corpus；计量结果生成 trace 与 report。`cli` 只解析参数与选择 artifact，不重算指标。`torch_policy` 是可选叶节点。

确定性边界：seed 显式传入；时间使用模拟整数；成本使用 integer micro-cost；浮点统计在产生点量化；JSON 使用 canonical codec；trace 每行带 checksum。

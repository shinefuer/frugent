# Synthetic workload

`generate_corpus(seed, size)` 只创建离线、可复现的编码任务描述。每项任务明确标记难度、共享前缀组、planted solution path 与 fictional optimal cost；它不是外部数据集，也不代表真实端点质量。

manifest 采用 canonical JSON fingerprint，fold 分配由 task ID 稳定推导。这样 baseline 与候选策略始终在同一批任务上配对比较。

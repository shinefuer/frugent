# Usage

库调用从 facade 开始：`PipelineConfig(seed=7, tasks=24)` 后传给 `run_pipeline`，得到 comparison、trace bytes、Markdown 与 HTML。单项调试可使用 `CachePolicy/replay_trace`、`Block/recall_curve`、`Budget/reserve`、`TraceHeader/export_trace`。

CLI 适合可重复实验：固定 `--seed` 和 `--tasks`；保存 artifact 时传 `--output`。配置、manifest、trace 与 report metadata 都包含 schema/version 或 fingerprint。

生产集成不在本项目范围。接入真实 adapter 前，应另行实现鉴权、租户隔离、真实 tokenizer 校准、速率限制与安全审计。

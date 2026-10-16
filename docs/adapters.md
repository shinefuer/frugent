# Model adapters

默认 adapter 只有 scripted 与 replay，两者都匹配 exact prompt bytes，不执行真实模型推理。`RecordingAdapter` 不改变 response，并保存精确 session；`export_session` / `import_session` 使用逐行 checksum 的 versioned JSONL 固化 request-response 顺序，可直接交给 `ReplayAdapter`。

`AdapterPlanner` 把离线 adapter response 中的 `kind\0payload` 记录转换为 plan→act→observe action。loopback HTTP 只允许 `http://127.0.0.1`、`localhost` 或 `::1`，用于本地 mock 测试；payload 不包含 API key 或 provider endpoint，且 timeout 与 response byte limit 都是硬边界。

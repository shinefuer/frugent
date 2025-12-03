# Model adapters

默认 adapter 只有 scripted 与 replay，两者都匹配 exact prompt bytes，不执行真实模型推理。RecordingAdapter 不改变 response，并保存精确 session。

loopback HTTP 只允许 `http://127.0.0.1`、`localhost` 或 `::1`，用于本地 mock 测试；payload 不包含 API key 或 provider endpoint。

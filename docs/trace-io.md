# Trace persistence

trace 首行为包含 run id、seed、config hash 与 fictional rate-card hash 的 v2 header；后续每个 event 单独 checksum，并要求 sequence 从 0 连续。任一行改动、截断或重排都会被拒绝。

fingerprint 对验证后的 exact bytes 求 SHA-256；`event_diff` 比较 logical sequence，`trace_diff` 还比较 run/seed/config/rate-card header，避免只改运行元数据却得到空 diff。两者都先验证完整输入，不忽略 schema。

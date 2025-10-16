# Trace persistence

trace 首行为包含 run id、seed、config hash 与 fictional rate-card hash 的 v2 header；后续每个 event 单独 checksum，并要求 sequence 从 0 连续。任一行改动、截断或重排都会被拒绝。

fingerprint 对验证后的 exact bytes 求 SHA-256；event diff 比较 logical sequence，不忽略 schema。

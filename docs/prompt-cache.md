# Prompt-cache lifecycle

entry 使用单调毫秒时钟、TTL 与 token capacity。TTL 在 `age >= ttl` 时到期；LRU/LFU 均有稳定 key 平局规则；admission 同时拒绝过小和永远无法容纳的 entry。

`replay_trace` 在 planted key trace 上测量 exact hit 与 cached token，不代表真实服务的 KV cache 行为或价格。

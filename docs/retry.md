# Retry and backoff

retry 只针对显式 transient code，max_retries 是硬上限。delay 使用 capped exponential backoff，jitter 由 seed 与 retry index 决定；相同输入产生相同 schedule。

cancellation 永远 terminal。attempt record 只累计真实执行到的等待，不把未发生的重试计入延迟。

# Cascade routing

model profile 的 cost/latency/success curve 全部来自 fictional rate card 与 scripted synthetic difficulty。ladder 要求成本与成功率不下降；confidence 和 verifier 同时通过才停止，否则按 retry budget 向上升级。

`cheapest_profile_at_floor` 先满足 quality floor 再比较成本，禁止通过降到 floor 以下制造“节省”。

# Prompt-cache routing

router 最大化已渲染 token sequence 的 cached prefix length，并可减去 queued-token penalty。平局按 instance name 稳定处理。小规模固定 cache snapshot 可穷举所有 assignment，作为 greedy 结果的可证明 optimum 对照。

这些 hit token 来自 planted prefix trace，不等同于真实服务端 KV 命中。

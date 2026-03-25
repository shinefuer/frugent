# Prompt-cache routing example

运行 `python examples/prompt_cache_routing/example.py result.svg`。脚本从空进程内构造两个 planted prefix cache 与三项 synthetic request，用 greedy 固定快照分配和 exhaustive optimum 比较，随后把实际命中 token 写成 SVG。

输出仅说明这个小型 planted trace 的机制行为，不代表真实端点的 KV cache、价格或延迟。

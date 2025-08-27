# Trace spans

span id 来自 seed、sequence 与 name，不使用 wall clock entropy。forest 验证 parent 存在、无环且 child timing 被 parent 包含；稳定 preorder 与 logical record 使相同执行产生相同 bytes。

exclusive duration 只在 direct siblings 不重叠时计算，避免把并行 wall time 错当成可加 CPU time。

# Prefix affinity

`PrefixTrie` 对已经渲染并分词的 prompt token sequence 建索引。`longest_prefix` 给出可复用 token 数；frequency 区分多个同长度候选；最终以 instance name 稳定打破平局。该指标只描述缓存亲和度，不推断模型质量。

插入记录 multiplicity，`remove` 一次删除一个 exact sequence 并只剪枝无用节点。持久化格式展开 exact sequence，便于 roundtrip 与 golden 检查；不保存实现内部 node shape。

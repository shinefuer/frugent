# Semantic result cache

exact retrieval 只接受规范化 prompt、tool name 与完整 canonical arguments 的 SHA-256 key。whitespace、Unicode NFKC 与显式 case folding 可形成等价类；tool argument value 不做 case folding。

shingle/MinHash 只发现 fuzzy candidate，绝不直接返回 response。调用方必须重新验证 exact key，因此 nonequivalent payload 不会因相似度或碰撞被服务。


## Immutable lifecycle state

`SemanticState` 保存 key-sorted exact entries 与 outcome log。lookup 先按 TTL purge，再只查 exact key；put 替换同 key，并按 `(created_at_ms, key)` eviction。versioned snapshot 以 response hex roundtrip，fingerprint 覆盖 entries 与 metrics。fuzzy candidates 从不进入 retrieval 路径。

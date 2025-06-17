# Semantic result cache

exact retrieval 只接受规范化 prompt、tool name 与完整 canonical arguments 的 SHA-256 key。whitespace、Unicode NFKC 与显式 case folding 可形成等价类；tool argument value 不做 case folding。

shingle/MinHash 只发现 fuzzy candidate，绝不直接返回 response。调用方必须重新验证 exact key，因此 nonequivalent payload 不会因相似度或碰撞被服务。

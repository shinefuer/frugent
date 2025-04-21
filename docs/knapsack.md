# Token-budget knapsack

每个 context block 有正整数 token weight 和 planted relevance value。小预算使用 exact dynamic programming，并以 key 做稳定平局决策；大问题可用 density greedy。`approximation_ratio` 只比较同一合成 item set 上的 planted value，不代表真实回答质量。

capacity curve 必须单调，所有选择的 token 总量都不超过预算。

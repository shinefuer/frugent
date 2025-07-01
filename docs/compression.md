# Context compression

sliding window 保留连续最新 suffix；extractive score 组合 recency、tool-output density、关键词和 synthetic planted relevance；小预算用 exact knapsack。

needle recall 只针对生成语料中的 planted key。degradation curve 来自实际选择结果，预算增加时 recall 不下降；它不代表真实模型回答质量。scripted summary hook 完全离线。

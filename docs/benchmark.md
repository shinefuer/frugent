# Synthetic benchmark metrics

所有比较使用相同生成任务的 paired counts。token savings、cache-hit uplift、cost-per-completed 和 simulated FIFO latency 都由实际离线执行记录计算；rate card 明确为虚构。

这些函数不会声称真实模型质量、provider 延迟或生产吞吐。`quality_preserved` 只检查 planted/scripted score 是否逐任务达到给定下限。

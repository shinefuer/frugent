# Evaluation methodology

1. 用同一 seed 生成 task ID、kind、difficulty、prefix group、planted solution path 与 optimal fictional cost。
2. baseline 和 stack 按 task ID 配对；不得丢弃失败项或更换 denominator。
3. 从实际计数计算 prompt/cache tokens、fictional micro-cost、completion 与 simulated queue latency。
4. paired delta 使用 seeded bootstrap interval；P50/P95 使用文档化线性插值。
5. quality preservation 仅指 planted task success 与 needle recall，不指真实模型评分。

报告携带 package version、seed、config hash、rate-card fingerprint 与 limitations。未执行的 coverage flag 不得写成成果。

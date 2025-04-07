# Synthetic statistics

统计函数只汇总同一 synthetic workload 上的配对运行。所有浮点结果在产生点量化到 6 位，bootstrap 使用显式 seed；P50/P95 来自记录的模拟 latency，不代表真实 endpoint。

`paired_deltas` 保留 task 顺序，`bootstrap_mean_ci` 对这些配对差值的均值重采样。曲线面积使用梯形法，并拒绝重复或逆序 x 坐标。

# Compression recall example

运行 `python examples/compression_recall/example.py result.svg`。脚本创建十个 synthetic message block，其中三个 key 是 planted needle；exact token-budget selection 在递增 budget 上实际计算 recall，并绘制无外部依赖的 SVG polyline。

曲线只覆盖此确定性 fixture，不外推到真实长上下文或模型总结质量。

# Cascade optimum example

运行 `python examples/cascade_optimum/example.py result.json`。三种 planted difficulty 各有 small/large scripted success 与 fictional cost，DP/exhaustive solver 在 quality floor 下寻找最低成本 policy；runtime policy 再计算 optimum gap。

`scripted_quality` 是合成成功曲线的加权值，不是任何真实模型评测。

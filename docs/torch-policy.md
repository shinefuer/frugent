# Optional PyTorch policies

`torch_policy` 仅在安装 `torch` extra 后加载 CPU PyTorch。confidence head 与 cache-admission demo 使用小型 synthetic binary labels；测试直接验证 seeded training loss 确实下降，但不把它解释为真实模型质量或线上效果。

默认运行时不需要权重、GPU、预训练模型或下载数据。训练产物只适用于生成它的 planted threshold 演示。

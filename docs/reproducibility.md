# Reproducibility

`uv.lock` 固定依赖；Python 支持 3.11/3.12/3.13。相同 seed/config/adapter bytes 应得到相同 workload fingerprint、decision order、trace bytes 与 report bytes。

重现顺序：创建 `.venv`，安装 `.[dev]` 或 `.[dev,torch]`，运行 `make build test-all format-check lint typecheck`，再执行四个 examples。CPU PyTorch 使用官方 CPU wheel index；不得下载预训练权重。

跨版本稳定性依赖 integer accounting、SHA-256、canonical JSON 和产生点六位量化。不要引入 wall clock 或无 seed random。

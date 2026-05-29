# Contributing

提交应聚焦一个可审查行为，并同时增加边界测试。运行 `make format build test format-check lint typecheck`；涉及 torch、integration 或 schema 时再运行 `make test-all` 与四个 examples。

新指标必须从执行计数推导，注明 synthetic/fictional/simulated 口径。新 schema 需 version、strict decoder、roundtrip、golden 与 migration。浮点值在产生点量化；随机性必须接收 seed。

提交信息使用 Conventional Commits。PR 说明机制、invariant、失败模式、验证命令与文档影响；不要提交 `dist/`、缓存、密钥、外部数据或模型权重。

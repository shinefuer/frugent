# References

这些资料只用于理解机制；frugent 的实现、schema 与测试均为独立代码。

- [FrugalGPT](https://arxiv.org/abs/2305.05176)：cascade 与成本/质量门控问题。
- [SGLang / RadixAttention](https://arxiv.org/abs/2312.07104)：prefix-aware KV reuse 的运行时动机。
- [vLLM Automatic Prefix Caching](https://docs.vllm.cc/en/latest/design/v1/prefix_caching.html)：block hash、allocation 与 eviction 概念。
- [GPTCache usage](https://github.com/zilliztech/GPTCache/blob/main/docs/usage.md)：semantic cache 的系统边界。
- [OpenTelemetry Trace](https://opentelemetry.io/docs/specs/otel/trace/)：span/attribute 语义参考。
- [ReAct](https://arxiv.org/abs/2210.03629)：交错 action/observation 的 loop pattern。
- [Python Packaging User Guide](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)：build backend。

本项目不复现上述论文实验，也不引用其真实性能数字作为自身结果。

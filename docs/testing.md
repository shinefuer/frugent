# Testing

`make test` 排除 `slow`；`make test-all` 包含 slow/model。未安装 torch 时 model tests cleanly skip；CI 安装 CPU extra。

测试层包括边界 validation、encode/decode golden、双向操作、randomized hard invariants、small exhaustive oracle、adapter/tool integration、CLI/example subprocess 与 pipeline byte determinism。关键性质包括 budget never overspend、semantic cache never poison、batch byte preservation、cost conservation、recall monotonicity 与 cascade quality floor。

测试不得连接公网、读取密钥、下载数据或依赖 wall clock。

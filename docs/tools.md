# Tool execution

executor 先运行 sandbox decision，再以 argv、`shell=False` 启动进程；denial 返回 126，timeout 返回 124，cancellation 返回 130，三者语义分离。stdout/stderr 以 bytes 保存，持久化用 hex，支持非 UTF-8 roundtrip。

`ScriptedTools` 要求 exact call order，适合完全离线 replay。dry-run 只输出 decision record。

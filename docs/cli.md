# CLI

`frugent route|cache|compress|batch|budget|trace` 分别观察单项机制；`bench` 在同一 synthetic corpus 上配对比较；`run` 串联全部阶段；`report --format markdown|html` 输出报告；`demo` 给出最短离线路径。

所有命令默认输出 canonical JSON；报告直接输出所选文档。`--output PATH` 写入文件。输入或文件错误返回 2，成功返回 0。`--seed` 与 `--tasks` 控制可复现工作负载；输出中的 cost 均为 fictional micro-cost。

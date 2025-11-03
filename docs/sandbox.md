# Sandbox policy

policy 以 argv token prefix、relative POSIX path glob 和 environment allowlist 表达。执行不经过 shell，但仍拒绝 shell metacharacter、控制字符、absolute path 与任何 `..` traversal，并返回首个精确 denial reason。

dry-run 只生成 decision trace，不执行命令。持久化记录保存 logical rule，不保存宿主环境值。

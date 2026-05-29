# Security

请通过 GitHub private vulnerability reporting 报告安全问题，并附最小复现、受影响版本和影响范围；不要在公开 issue 中披露未修复漏洞。维护者会先确认收件，再评估修复与公告。

`sandbox` allowlist 负责确定性 policy decision，但不是内核级隔离。调用者仍应在低权限 container/process 中执行工具，限制挂载与网络，并避免传入 secrets。semantic fuzzy candidates 不可直接返回结果；exact normalized key 才能 retrieval。trace/report 应按敏感日志处理。

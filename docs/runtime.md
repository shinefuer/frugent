# Agent loop

runtime 实现 plan → act → observe，action 只有 tool、answer、cancel。step budget 统计 act 次数；cancel 在调用 tool 前终止。scripted planner 与 bytes tool 让默认测试完全离线。

event sequence 连续，payload 以 hex 保存；相同 action、tool、seed 派生输入产生 byte-identical record 与 fingerprint。

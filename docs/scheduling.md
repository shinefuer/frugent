# Budget scheduling

task 先按 priority、token estimate、id 确定顺序。admission 同时检查 token 与 fictional micro-cost，任何接受集合都不超支。fair share 用 priority+1 权重和 largest remainder 分配整数资源，总量精确守恒。

相同 task/config 必须产生相同 decision record；降级顺序为 full、downgrade、compress、cache_only、defer。

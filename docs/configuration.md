# 配置与复现

`RuntimeConfig` 使用整数 token 与微单位成本预算，避免货币累计中的浮点歧义。当前 schema 为 v2；加载器只接受完整字段集合，拒绝未知字段，并能把明确支持的 v1 字段迁移到 v2。

配置输出采用键排序、无多余空白的 UTF-8 JSON。`fingerprint` 对生效后的完整记录计算 SHA-256，可放入 trace 与报告 metadata。相同配置、seed 和离线 adapter 应产生相同 fingerprint；任何预算或质量下限变化都会改变它。

配置不会包含 endpoint、API key 或真实服务价格。项目的成本实验统一使用单独的虚构 rate card。

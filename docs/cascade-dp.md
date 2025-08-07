# Cascade policy oracle

每个 synthetic difficulty 可选择 scripted action；DP/oracle 计算 mixture 上的 expected fictional cost 与 scripted success。小空间完整枚举，选择满足 quality floor 的最低成本 policy，并输出 Pareto frontier。

runtime policy 若低于 floor，`optimum_gap` 直接拒绝，不能把质量下降包装为成本改进。

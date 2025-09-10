# Cost attribution

prompt、completion、cache saving、batch saving 与 explicit adjustment 均以整数微单位记录。rollup 对每个 component 分别求和；parent 与 children 的差异只能通过显式 adjustment 表达。

rate-card conversion 直接复用已经计算的 breakdown，不在 trace 层重新计价。group 可按 task/session/tool/model label 汇总。

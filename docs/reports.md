# Reports

报告器只消费本次运行得到的计数、模拟延迟与 fictional micro-cost。Markdown 表、内嵌 SVG 和 self-contained HTML 均由标准库确定性生成；输入中的 HTML 会转义。

每份报告携带版本、seed、config hash 与 rate-card fingerprint，并根据实际 coverage flags 生成 limitations。报告不把离线 adapter 或 planted task success 描述成真实模型评估。

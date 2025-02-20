# 虚构 rate card

frugent 的所有成本都来自 `RateCard`，单位为整数微单位/1000 token。卡片标签必须明确包含 `fictional`，从数据层阻止合成价格被误解为真实 provider 报价。

prompt 成本拆为未缓存与缓存 token；缓存部分乘 `cache_price_ppm`，批处理再对总额应用 `batch_price_ppm`。所有除法向上取整，确保预算调度不会因截断而少计成本。`CostBreakdown` 与 `Savings` 分别验证总成本和节省归因守恒。

`demo_rate_card()` 只服务离线 scripted workload。其数值是示例参数，不代表真实价格、服务质量或延迟。

# Public API

稳定入口位于 `frugent` facade：configuration/rate card、record/context、cache/compression/batching、cascade/budget、trace/sandbox、offline adapter/runtime、synthetic workload/pipeline/report。`frugent.__all__` 是排序且无重复的 golden inventory。

更细的实验函数仍可从对应模块导入，但不属于 facade 稳定集合。所有 facade 类型都不触发网络、模型或文件写入；只有显式执行函数才产生结果。

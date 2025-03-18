# Context store

`MessageStore` 是 immutable append-only value，version 等于消息数。旧 value 不会随新消息改变，因此 snapshot 可安全复用。`diff(base, target)` 只接受 target 完整继承 base 的情况；`apply_diff` 同时校验 base version，从而避免把 suffix 应用到错误历史。

持久化记录包含 schema、version 与完整消息列表；恢复时重新验证每条 `Message`，并核对 version。fingerprint 覆盖这些字段，可用于 replay 与报告 metadata。

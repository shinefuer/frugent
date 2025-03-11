# Token accounting

默认 `HeuristicTokenizer` 是稳定的离线词法计数器，并不模拟任何 provider tokenizer。所有预算机制接收 `Tokenizer` protocol，因此测试可以注入严格可控的计数器。

`render_prompt` 使用固定 role delimiter，`count_prompt_by_role` 提供归因；`truncate_tokens` 只在已识别 token 边界裁剪。微型 BPE trainer 只展示确定性 merge 机制，训练样本由调用方提供，不下载 vocabulary 或模型。

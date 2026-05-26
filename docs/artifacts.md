# Artifact schemas

| Artifact | Version | Integrity |
|---|---:|---|
| RuntimeConfig | 2 | canonical fingerprint; v1 migration |
| context/message store | 1 | canonical fingerprint |
| rate card | 1 | full-card fingerprint |
| workload manifest | 1 | synthetic flag + SHA-256 |
| span/tool/runtime records | 1 | strict field set |
| trace JSONL | 2 | checksum per line; v1 header migration |
| report | metadata version | exact-byte fingerprint |

Decoder 遇到 unknown field、错误 type、checksum mismatch 或不连续 sequence 时失败；schema 变化需同步 golden tests 与 changelog。

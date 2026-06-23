# 系统智能体运行契约与代码规范 (AGENTS.md)

## 1. 角色定义与愿景 (Persona & Vision)
本智能体作为量化交易与高级全栈工程思维相结合的系统，极度注重数据确定性、系统健壮性、风险边际以及零信任防御性编码。

## 2. 核心行为准则 (Behavioral Constraints)
* **人工审计卡点：** 在运行、提交或合并任何代码修改前，均须向用户提供详细的变更解释和 Diff。在关键步骤未取得 Gatekeeper 的 "Proceed" 确认前，不得擅自推进。
* **数据流安全审计：** 涉及任何数据流入流出、报错日志输出时，必须优先进行安全性检查，防止由于异常捕获不当导致敏感信息泄漏。
* **最高确认权追加：** 用户（人类 Gatekeeper）拥有最高审计和代码 Diff 确认权。Agent 在执行代码修改、安装依赖、运行脚本或准备 Git 提交前，必须暂停并等待人类发送 "Proceed"。

## 3. 代码规范铁律 (Coding Rules)

### A. 防限流与缓存机制 (Anti-Rate-Limiting)
* 所有外部 API 请求必须使用缓存机制（例如对频繁请求进行 local cache/ttl=3600 处理，或加入请求延迟），以防止触发第三方 API 的限流（429 Too Many Requests）或被防火墙拦截。

### B. 零信任安全脱敏与日志审计 (Zero-Trust Logging)
* **严禁泄露密钥：** 严禁在日志、标准输出或调试信息中打印任何真实的 API Key、Token、Password 或 Secret。
* **脱敏过滤：** 日志捕获机制必须通过安全补丁，自动洗练并将敏感匹配项（包含 `KEY` / `TOKEN` / `SECRET` 等）替换为 `***` 或 `*****`。

### C. 防御性异常处理 (Defensive Exception Handling)
* 所有外部 API 调用（如使用 `requests` 库发起的网络请求）必须强制包裹在完整的 `try-except` 异常捕获块中，确保即使单次请求失败，程序依然可以平稳运行而不崩溃。

### D. 数值安全防护 (Zero-Division & Alignment)
* 零分母防护：计算任何比例或标准差时，内置对除数的“防零/防空值（Zero-Division Patch）”安全过滤。
* 对齐防护：在计算多数据源对齐时，统一使用强时间序列对齐，严禁易导致索引错位的 Resampling 机制。

# 数据获取节点 (Node 1) 架构设计 (architecture.md)

本文档记录了 AI 求职助手数据获取节点 (Node 1) 的架构布局与数据流向。

## 1. 节点定位
数据获取节点主要负责从目标平台检索、标准化、去重并暂存招聘岗位数据。确保数据一致性，并对限流策略与服务器异常具备高防御性（防御性编码）。

## 2. 目标数据源

```
+-----------------------------------------------------------------------+
|                      数据获取节点 (Data Ingestion Node 1)               |
+------------------+--------------------------------+-------------------+
                   |                                |
                   v                                v
         [ReliefWeb API v2]             [Swiss Job-Room 检索接口]
       - 地点: Geneva/Switzerland       - 地点: Genève/Remote
       - 聚焦: 联合国/NGO/国际组织职位     - 聚焦: 瑞士政府/官方发布职位
```

### A. ReliefWeb API (v2)
* **API 接口:** `https://api.reliefweb.int/v2/jobs`
* **筛选器:** 国家/地点（`Switzerland` / `Geneva`），并匹配搜索关键词。
* **数据输出:** 包含职位描述 (JD)、发布机构以及直达申请链接的 JSON 数据。

### B. Swiss Job-Room 检索接口
* **API 接口:** 针对瑞士官方 Job-Room 系统，在抓取脚本中使用公开的检索端点 `https://www.job-room.ch/secoalv/api/v1/jobAdvertisements/search` 进行直接查询。
* **筛选器:** 地点（`Genève` 或 `Remote`），并遍历 11 个关键词。
* **数据输出:** 经过清洗的瑞士政府公开职位列表。

---

## 3. 数据处理管线 (Pipeline)

1. **输入与动态关键词提取 (动态输入层):**
   * 用户通过 **Streamlit** 前端界面上传个人简历 (PDF/Word/Text)。
   * 调用 **Gemini API** 动态分析简历，提取候选人的技能特征与求职意向，动态生成 5~10 个核心关键词。
   * 前端进行 **人工确认 (Human-in-the-loop)**：用户可在界面审核、修改、增删提取的关键词。系统设定硬熔断上限，总数绝对禁止超过 20 个，以防止 API 滥用与并发超载。
2. **多数据源精确检索 (Ingestion Layer):** 依据最终确认的关键词列表（上限 20 个），循环检索 ReliefWeb 与 Swiss Job-Room 数据源。如果系统判定没有自定义提取的词（例如提取失败或空白上传），则自动触发优雅降级安全网，默认只遍历 1 个保底核心关键词 ["Project Manager"] 进行数据检索，拒绝无效的高频遍历，从而严格控制第三方 API 调用的并发风险与防限流控制（Rate Limiting）。
3. **防限流保护与缓存 (Rate Limit Guard & Caching):** 在每次 API 请求之间引入毫秒级延迟，并对请求执行本地 TTL=3600 缓存，防止触发 429 限流或被安全盾拦截。
4. **数据标准化 (Data Normalization):** 将不同源的多样字段统一映射为标准 Schema：
   * `title` (职位名称)
   * `company` (公司/组织名称)
   * `link` (原始招聘详情链接)
   * `description` (纯文本格式的职位描述 JD)
5. **数据去重 (Deduplication):** 依据职位详情 URL 或 [职位名称 + 公司哈希] 进行碰撞检测，排除重复岗位。
6. **本地存储 (Storage):** 将最终去重后的聚合数据输出到根目录下的 `easy_jobs_pool.json`。

## 4. 前端交互与状态管理 (State Management)
* **技术选型：** 使用 Streamlit 构建前端交互看板。
* **状态锁存：** 为了避免用户在前端交互（如点击检索、增删关键词等）时导致 Streamlit 重新运行整个脚本而重复调用大模型 API，提取出的关键词必须锁存在 Streamlit 的 `st.session_state` 中。在后续操作中直接读取锁存状态，绝对禁止二次触发 Gemini API 调用，锁定 Token 成本并防止 API 滥用。

## 5. 简历/求职信自动定制系统 (Personalization Engine)
* **技术实现：** 编写独立模块 `tailor_agent.py`，暴露核心函数 `generate_tailored_materials(cv_text, jd_text)`。
* **业务匹配规则：** 自动交叉比对候选人简历与职位描述 (JD)，深入结合其“媒体项目经理（Media Project Manager）、管理多市场、负责程序化广告与社媒投放”的高价值核心资历，生成高转化率的定制求职信。
* **锁存防刷：** 针对每一个岗位的定制结果，必须锁存在 `st.session_state` 的专属键中，防止触发 UI 重绘时的二次 Token 消耗。

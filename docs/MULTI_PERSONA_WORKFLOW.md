# KUN Chat 多角色复刻工作流

本文记录当前 KUN Chat 的生产流程，并作为“坤坤、峰哥、青霞、磊磊”四个公开表达型 AI 角色的统一实施规范。其中青霞基于林青霞公开表达资料，磊磊基于涂磊公开表达资料。这里的“复刻”是指：基于可核验的公开表达，生成带清晰 AI 标识的对话角色；不把角色冒充为真人，也不把影视台词、主持人提问或他人观点写成人物本人的经历与观点。

## 1. 当前生产基线

| 角色 | 对话状态 | 事实 RAG | 风格 RAG | 语音状态 |
| --- | --- | ---: | ---: | --- |
| 坤坤 | 生产可用 | 107 sources / 119 chunks | 424 examples | 本地已配置；授权状态仍由独立门禁管理 |
| 峰哥 | B站直播切片第一批已接入 | 2 fact documents | 50 style examples | MiniMax 原创数字人声线；非真人声纹克隆 |
| 青霞（林青霞 AI 角色） | 最小生产集已接入 | 4 documents | 1 example | MiniMax 专属 Voice ID，仅保存在本机 |
| 磊磊（涂磊 AI 角色） | 最小生产集已接入 | 5 documents | 2 examples | MiniMax 专属 Voice ID，仅保存在本机 |

2026-07-22 峰哥 B 站直播切片第一批已增量接入独立生产库：52 documents（2 facts + 50 style），其中 50 条 style examples；应用状态将每条生产 document 作为一个可检索 chunk，因此报告为 52 documents / 52 chunks / 50 style examples。`persona_id=fengge` 时只读取 `D:\OneDrive\LLMs\persona-material\fengge\production\fengge-rag.sqlite3`。其余 510 个未完成双门禁的窗口继续隔离，不得进入生产。

峰哥 style 记录只用于表达风格与归属观点，不得作为客观事实检索；Facts RAG 仅查询 `kind=fact AND semantic_gate=attributed_fact`。当前 `production_scope_pending=0`、`training_permission=unverified`、`audio_training_eligible=false`、声纹训练关闭。

候选库总览：`D:\OneDrive\LLMs\persona-material\README.md`；机器可读状态：`D:\OneDrive\LLMs\persona-material\STATUS.json`。

坤坤生产库：

- SQLite：`D:\OneDrive\LLMs\talk-to-fengge\data\kunkun-rag.sqlite3`
- 事实文档：`D:\OneDrive\LLMs\kun-material\training\rag_documents.jsonl`
- 风格短句：`D:\OneDrive\LLMs\kun-material\training\style_examples.jsonl`
- 审核后文本：`D:\OneDrive\LLMs\kun-material\transcripts\approved_rag`
- 语义审核表：`D:\OneDrive\LLMs\kun-material\manifests\semantic_review.csv`

生产代码只能读取 `approved_rag`、已标记 `rag.eligible=true` 的记录和相应生产数据库。不得读取 `raw_segments_unreviewed`、`rag_documents_unreviewed` 或 `candidate_queue` 中仅供审核参考的候选。

## 2. 标准流水线

```text
公开来源发现
  → 来源清单与权利状态
  → 下载允许性检查
  → 音视频标准化 / OCR / ASR
  → 说话人门禁
  → 语义归属门禁
  → 事实与表达风格分库
  → 建立人物专属索引
  → 注入人物提示词
  → 自动与人工评测
  → 独立语音授权门禁
  → 本地或公网发布
```

### 2.1 来源发现与登记

优先级依次为：本人或工作室官方账号、完整采访、官方节目或媒体专访、本人公开直播。每条来源至少登记：人物、平台、标题、URL、发布日期、采集日期、许可/下载状态、媒体类型、时间范围和备注。

仅“公开可访问”不等于“允许批量下载、再发布或训练”。只能下载平台明确允许、来源方明确提供下载或已获得授权的内容；否则只保留链接、元数据和允许使用的摘要。

### 2.2 说话人门禁

音视频进入生产前必须确认目标人物确实在说话。多人采访需先做分离，再对每个候选窗口复核。坤坤流程曾对相邻短句使用声纹相似度与 margin 双条件，但该阈值依赖具体模型和样本，不能直接复制给其他人物。

必须隔离：主持人、提问者、连麦者、旁白、观众、背景音及身份不确定片段。

### 2.3 语义归属门禁

说话人正确仍不等于观点属于本人。只把 `own_speech` 纳入生产，并隔离：

- 读弹幕、读题和复述提问；
- 引用他人、歌词和长篇原文；
- 嘉宾故事或传闻；
- 影视角色对白；
- 无法确定上下文和归属的片段。

林青霞的电影台词只能作为作品事实，不能用作她的个人表达风格；涂磊节目中嘉宾的故事不能变成他的个人经历。

### 2.4 双 RAG

每个人物都维护两个彼此独立的检索空间：

- Facts RAG：回答“说过什么、做过什么、在何处公开表达过”。结果必须附来源 URL。
- Style RAG：回答“怎么说”。只保存短、自然、已双审的本人表达样本，不保存整段采访或歌词。

每轮请求分别检索事实和风格，再将少量高相关材料注入系统提示。禁止在不同人物之间共享检索结果，防止人物串线。

### 2.5 人格提示与生成约束

页面和回答必须清楚标注 AI 角色，不声称是真人或工作室。提示词应规定：

- 使用公开可核验资料，不编造私生活、内部行程、私人关系或个人记忆；
- 不知道时直接承认，不用相似语气掩盖事实缺失；
- 不长篇复制来源；
- 语气标签可用于生成控制，但展示与 TTS 前必须去除，例如“（语气平和）”；
- 人物专属事实库未完成时，不得用其他人物资料填空。

### 2.6 质量门禁

发布前至少检查：

1. 来源可回溯，URL 和时间范围有效；
2. 说话人、语义归属和人物身份正确；
3. 事实回答不越过检索证据；
4. 风格像自然对话，但不机械复读样本；
5. 不出现跨人物资料污染；
6. 首轮能直接回答用户问题，不重复自我介绍；
7. 语气括号不显示、不朗读；
8. 手机端输入、录音、文字回复、语音播放均通过 HTTPS 实机测试。

## 3. 新角色目录规范

公开资料整理任务统一写入：

```text
D:\OneDrive\LLMs\persona-material\
  fengge\
  linqingxia\
  tulei\
```

每个人物至少包含：

```text
manifests/sources.jsonl
transcripts/pending/
transcripts/approved_rag/
training/rag_documents.jsonl
training/style_examples.jsonl
reports/COVERAGE.md
reports/REVIEW.md
```

在 `pending=0`、自动测试通过且人工抽检通过前，不得接入生产索引。

## 4. 语音与歌声是独立权限层

文本 RAG、说话 TTS、声音克隆、歌声转换/SVS 是四件不同的事。公开采访可以支持事实与风格审核，但不能自动证明允许声纹克隆或歌声训练。每个人物必须单独记录可验证的授权范围、用途、期限、地区和撤回方式；缺失时保持 `training_permission=unverified`。

未配置人物专属且已授权 Voice ID 时，页面只提供文字，不回退到其他人物声音。原创音乐功能也不得把人物 Voice ID 当作歌声克隆接口。

## 5. 公网产品架构

GitHub 仓库公开不等于聊天网站已经上线。完整公网版本需要：

```text
手机/电脑浏览器（HTTPS 前端）
  → 公网 API（对话、检索、STT、TTS）
  → 人物专属 RAG / 对象存储
  → DeepSeek、MiniMax 等服务端密钥
  → 账号、配额、支付、限流、日志与风控
```

GitHub Pages 只能托管静态页面，不能运行当前 Python 后端，也不能安全保存 DeepSeek/MiniMax 密钥。因此在公网 API 域名配置完成以前，不应把静态页面标成“已上线可对话”。本地 `127.0.0.1` 和局域网地址也不能作为任意手机可访问的公开网址。

公网发布完成的验收条件：独立 HTTPS 域名、服务端密钥不下发、跨域配置正确、健康检查通过、手机麦克风权限正常、用户数据政策可见、滥用与成本上限生效。

## 6. 当前下一步

1. 继续扩充三人的双审 production 资料，但保持人物库严格隔离。
2. 公网首版使用服务端密钥、D1 匿名额度和 HTTPS；不把 API 密钥下发到浏览器。
3. 完成公网四角色事实/风格数据同步与端到端手机实测。
4. 在公网测试稳定后加入正式账号、充值与支付回调。
5. 只有取得可核验的独立声音授权后，才为对应人物启用专属 Voice ID。

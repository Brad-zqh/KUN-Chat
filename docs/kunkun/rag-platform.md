# DeepSeek + 本地公开语料 RAG 平台

## 架构

1. 独立任务持续把公开音频、元数据和 Whisper 字幕写入 `D:\OneDrive\LLMs\kun-material`。
2. `worker/rag_store.py` 只读取已经完整落盘、且至少 3 秒未修改的字幕/文本；忽略音频、临时下载与 `.part` 文件。
3. 字幕按约 420 字切片，生成中文二/三字词索引并写入本地 SQLite FTS5。索引支持增量更新，不需要 GPU，也不需要训练模型。
4. 用户提问时，先检索相关片段，再把人格提示、检索上下文和对话历史一起发送给 DeepSeek API。
5. 网页在回复下面显示命中的公开资料标题与原始 URL。
6. TTS 可通过 `.env.local` 切换本地 VoxCPM 或 MiniMax 云端语音。

## 配置

```env
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=在本机填写

KUN_MATERIAL_DIR=D:\OneDrive\LLMs\kun-material
KUN_RAG_DB=D:\OneDrive\LLMs\talk-to-fengge\data\kunkun-rag.sqlite3
```

如使用 MiniMax TTS：

```env
TTS_PROVIDER=minimax
MINIMAX_API_KEY=在本机填写
MINIMAX_VOICE_ID_KUNKUN=已获授权的VoiceID
MINIMAX_TTS_MODEL=speech-2.8-turbo
```

## 手动检查

```powershell
& "D:\LocalDevDeps\OneDriveMirror\LLMs\KUN-Chat\.venv\Scripts\python.exe" -m worker.rag_store --query "舞台紧张怎么办"
```

网页入口：`http://127.0.0.1:8766/chat.html`

## 数据质量边界

自动转写可能包含主持人、旁白、其他嘉宾和识别错误。系统提示会要求模型把片段作为不可信参考材料，而不是把每句话都归因于蔡徐坤。后续可增加说话人分离与人工校验，改善人格语料纯度。

# KUN Chat

<p align="center">
  <a href="README.md">English</a> · <strong>简体中文</strong>
</p>

<p align="center">
  <a href="https://brad-zqh.github.io/KUN-Chat/">项目主页</a> ·
  <a href="https://brad-zqh.github.io/KUN-Chat/?lang=zh">中文网站</a> ·
  <a href="docs/kunkun/production-rag-baseline.md">RAG 生产基线</a>
</p>

KUN Chat 是一个可部署的 AI 数字人平台，集成经过审核的检索增强生成、
本地语音识别、文本转语音和多模型路由。项目展示了从语料治理、角色编排，
到账号控制与公网部署的完整 AI 应用工程链路。

项目最初是一个基于公开表达风格笔记和明确审核通过的本地 RAG 语料库构建的
AI 同人角色界面。项目与蔡徐坤本人、工作室或相关团队无隶属、背书或运营关系。

公开仓库仅包含应用代码，**不包含** API 密钥、真人克隆语音、语音训练样本、
私人聊天数据或生产环境的本地 RAG 数据库。

## 功能特性

- 适配桌面端与移动端的蓝色主题响应式聊天界面
- 自动识别浏览器语言的中英双语项目主页
- 多角色独立系统提示、RAG 知识库、聊天历史与语音配置
- DeepSeek 或 MiniMax 文本生成
- 双层 RAG：事实片段决定“说什么”，口语样本辅助“怎么说”
- 人物表达习惯建模：常用词、句式、语气和回答结构保持角色一致性
- 未审核候选资料默认拒绝进入生产 RAG
- 浏览器录音及移动端系统录音回退
- 本地 Whisper 中文语音识别与角色专名提示
- 面向拥有独立、可验证授权说话者的高保真 MiniMax / VoxCPM 个性化语音合成
- 可选 MiniMax Music 3.0 原创清唱实验（仅文字生成音乐）
- 界面中明确展示 AI 数字人身份与责任边界

## 系统架构

```text
浏览器文字 / 按住说话
          ↓
本地 Whisper 识别 + 角色专名提示
          ↓
已审核事实 RAG + 口语风格检索
          ↓
DeepSeek / MiniMax 模型路由
          ↓
有依据的回答 + 来源链接 + 授权 TTS
```

GitHub Pages 层完全静态，不保存任何模型服务商凭据。聊天、RAG、语音识别、
身份验证、配额和语音合成都运行在独立部署的 Python 服务端。

## 本地运行

环境要求：Python 3.11–3.14。

```powershell
Copy-Item .env.example .env.local
# 仅在 .env.local 中填写你自己的服务商凭据。
uv sync
uv run python -m worker.web_server
```

在电脑浏览器中打开 <http://127.0.0.1:8766/chat.html>。同一可信 Wi-Fi 下的手机
可以访问 `http://<电脑局域网IP>:8766/chat.html`。普通 HTTP 页面无法直接调用
`getUserMedia` 时，页面会回退到手机系统录音功能。

## RAG 数据边界

默认生产资料目录为：

```text
<KUN_MATERIAL_DIR>/transcripts/approved_rag
```

运行时会拒绝目录名不是 `approved_rag` 的生产数据源。未审核分段导出和
`candidate_queue.jsonl` 永远不会进入生产输入。当前已验证基线为
**105 个来源 / 117 个事实片段 + 424 个风格样本**。详见
[生产 RAG 基线](docs/kunkun/production-rag-baseline.md)。

## 语音与身份边界

媒体内容公开可访问不等于获得真人语音训练或克隆许可。本仓库不分发克隆语音，
也不包含真人语音样本。仅当拥有来自发声者或权利人的独立、可验证授权时，
才应配置 TTS Voice ID。

当前文档标记：`training_permission=unverified`。

## 部署说明

GitHub Pages 只能托管静态前端。聊天、RAG、STT 和 TTS 需要独立后端，并通过
服务器环境变量保存密钥。请勿把服务商密钥写入浏览器代码或公开的 Pages 配置。

## Windows 自动同步

首次安装每五分钟运行一次、默认拒绝风险文件的同步任务：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-auto-sync.ps1
```

任务只暂存已记录的代码路径，检查凭据与运行时媒体文件，执行单元测试，之后才会
提交并推送 `main`。冲突或测试失败会停止同步且不会强制推送。日志位置为
`%LOCALAPPDATA%\KUN-Chat\github-sync.log`。

卸载同步任务：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\uninstall-auto-sync.ps1
```

## 原创清唱实验

设置 `KUN_MUSIC_ENABLED=true`，并将 MiniMax API Key 保留在服务器端。浏览器只调用
`/music/generate`，不会接触密钥。该接口仅使用 `music-3.0` 或 `music-3.0-free`
文字生成音乐，明确拒绝参考音频、翻唱模型、克隆 Voice ID 和未经确认的歌词。
生成链接为临时链接，通常约 24 小时后过期。

## 测试

```powershell
uv run python -m unittest discover -s tests -v
```

## 许可证

请参阅 [LICENSE](LICENSE) 与 [NOTICE](NOTICE)。

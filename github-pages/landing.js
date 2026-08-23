(() => {
  const copy = {
    zh: {
      title: "KUN Chat · AI 数字人平台",
      description: "KUN Chat：通过双层 RAG 保留人物表达习惯，并以授权个性化语音模型还原专属声音的 AI 数字人平台。",
      brandTag: "AI 数字人对话平台", repository: "代码仓库",
      eyebrow: "双层 RAG · 表达习惯 · 高保真授权语音",
      heroTitle: "让 AI 角色保留<br><span>表达习惯与专属声音</span>",
      heroLead: "大语言模型结合事实与风格双层 RAG，学习特定人物常用词、句式、语气和回答结构；在获得可验证授权后，个性化语音模型进一步高保真还原其音色、语速、停顿与表达节奏。",
      tryProduct: "体验在线版本 ↗", viewCode: "查看 GitHub 代码",
      metricPersonas: "独立角色", metricGrounded: "可溯源回答", metricVoiceValue: "VOICE AI", metricVoice: "高保真授权语音",
      pipelineLabel: "交互链路 / Interaction pipeline",
      flowInputTitle: "文字或语音输入", flowInputBody: "浏览器录音 · Whisper 中文识别",
      flowRagTitle: "角色化 RAG 检索", flowRagBody: "事实片段 · 口语风格 · 来源追踪",
      flowReplyTitle: "角色化生成与高保真语音回复", flowReplyBody: "LLM 回答 · 授权声音建模 · TTS 播放",
      voiceTitle: "不只是回答问题，<br>而是保留人物的表达与声音",
      voiceBody: "风格 RAG 从经过审核的表达样本中检索常用词、句式、语气和叙述结构，让语言模型生成更符合人物习惯的回答；授权 Voice ID 再学习可感知的声音特征，使内容与声音保持一致。",
      voiceStyle: "用词句式 · Style patterns", voiceTimbre: "音色还原 · Timbre", voiceCadence: "语速节奏 · Cadence", voicePauses: "停顿表达 · Pauses", voiceConsistency: "角色一致性 · Consistency",
      voiceBoundary: "仅对拥有独立、可验证授权的说话者启用个性化语音能力。",
      capTitle: "工程能力", capLead: "从资料治理到公网部署，项目覆盖了完整的 AI 应用链路，而不仅是一个聊天界面。",
      capRagTitle: "双层 RAG", capRagBody: "将事实依据与表达风格分离检索，并对未审核材料采取默认拒绝策略。",
      capVoiceTitle: "高保真角色语音", capVoiceBody: "结合按住说话、Whisper 识别、角色专名提示与授权个性化 TTS，形成自然的双向语音对话。",
      capDeployTitle: "生产化部署", capDeployBody: "静态前端与服务端密钥隔离，配套账号、配额、监控和自动部署流程。",
      capSafetyTitle: "安全边界", capSafetyBody: "明确 AI 身份、授权边界与数据来源，不将私人资料或密钥写入公开仓库。",
      roleTitle: "多角色体验", roleLead: "每个角色拥有独立的系统提示、知识库、对话历史与可选语音配置。",
      roleKun: "坤坤", roleKunNote: "音乐与舞台", roleFeng: "峰哥", roleFengNote: "直接、具体观点",
      roleCan: "老残", roleCanNote: "阅读与表达", roleQiu: "皓哥", roleQing: "清凉山人", roleNai: "奶奶",
      roleYuxin: "雨芯", roleYuxinNote: "独立 RAG", authorized: "授权数字人",
      openTitle: "开源代码，中英双语文档",
      openBody: "在 GitHub 查看系统架构、RAG 数据边界、本地运行方式和部署说明。项目文档同时提供 English 与简体中文版本。",
      openButton: "浏览代码仓库 →",
      notice: "所有角色均为 AI 数字人，不代表真人本人、团队或工作室。生成内容不应被视为真人声明、投资意见或专业建议。语音能力仅在具备可验证授权时启用。"
    },
    en: {
      title: "KUN Chat · AI Persona Platform",
      description: "KUN Chat uses dual-layer RAG to preserve distinctive speaking patterns and authorized voice models to deliver high-fidelity persona voices.",
      brandTag: "AI Persona Conversation Platform", repository: "Repository",
      eyebrow: "Dual-layer RAG · Speaking Patterns · Authorized Voice AI",
      heroTitle: "AI personas that retain<br><span>distinctive expression and voice</span>",
      heroLead: "A dual-layer fact-and-style RAG pipeline captures recurring vocabulary, sentence patterns, tone, and response structure. With independently verifiable authorization, a personalized voice model further reproduces the speaker's timbre, pace, pauses, and delivery at high fidelity.",
      tryProduct: "Try the live product ↗", viewCode: "View source on GitHub",
      metricPersonas: "Independent personas", metricGrounded: "Traceable answers", metricVoiceValue: "VOICE AI", metricVoice: "Authorized high-fidelity voice",
      pipelineLabel: "Interaction pipeline",
      flowInputTitle: "Text or voice input", flowInputBody: "Browser recording · Whisper ASR",
      flowRagTitle: "Persona-aware retrieval", flowRagBody: "Facts · Speaking style · Source tracing",
      flowReplyTitle: "Persona-aware generation and voice reply", flowReplyBody: "LLM response · Authorized voice profile · TTS",
      voiceTitle: "More than answering questions—<br>consistent expression and voice",
      voiceBody: "Style RAG retrieves recurring vocabulary, sentence structures, tone, and narrative patterns from reviewed examples, guiding the language model toward the persona's speaking habits. An authorized Voice ID then models perceptible vocal characteristics so content and delivery remain consistent.",
      voiceStyle: "Wording · Style patterns", voiceTimbre: "Voice color · Timbre", voiceCadence: "Pace · Cadence", voicePauses: "Delivery · Pauses", voiceConsistency: "Persona · Consistency",
      voiceBoundary: "Personalized voice features are enabled only for speakers with independent, verifiable authorization.",
      capTitle: "Engineering highlights", capLead: "From corpus governance to public deployment, the project covers an end-to-end AI application stack—not just a chat UI.",
      capRagTitle: "Dual-layer RAG", capRagBody: "Retrieves factual grounding and speaking style separately, with fail-closed exclusion of unreviewed data.",
      capVoiceTitle: "High-fidelity persona voice", capVoiceBody: "Combines push-to-talk, Whisper ASR, persona name hints, and authorized personalized TTS for natural two-way voice conversations.",
      capDeployTitle: "Production deployment", capDeployBody: "Separates the static client from server-side secrets, with accounts, quotas, monitoring, and automated delivery.",
      capSafetyTitle: "Responsible boundaries", capSafetyBody: "Makes AI identity, authorization, and data provenance explicit while keeping private data and credentials out of the public repo.",
      roleTitle: "Multi-persona experience", roleLead: "Each persona has an independent system prompt, knowledge base, conversation history, and optional voice configuration.",
      roleKun: "Kunkun", roleKunNote: "Music & performance", roleFeng: "Fengge", roleFengNote: "Direct, concrete views",
      roleCan: "Laocan", roleCanNote: "Reading & expression", roleQiu: "Qiuhao", roleQing: "Qingliang Shanren", roleNai: "Grandma",
      roleYuxin: "Yuxin", roleYuxinNote: "Independent RAG", authorized: "Authorized persona",
      openTitle: "Open source, bilingual documentation",
      openBody: "Explore the architecture, RAG data boundaries, local setup, and deployment notes on GitHub. Project documentation is available in both English and Simplified Chinese.",
      openButton: "Explore the repository →",
      notice: "All characters are AI personas and do not represent the real individuals, their teams, or studios. Generated content should not be treated as real-person statements, investment advice, or professional guidance. Voice features are enabled only with verifiable authorization."
    }
  };

  const params = new URLSearchParams(location.search);
  const saved = localStorage.getItem("kun-site-language");
  let language = params.get("lang") || saved || (navigator.language.toLowerCase().startsWith("zh") ? "zh" : "en");
  if (!copy[language]) language = "en";

  function applyLanguage(next, updateUrl = false) {
    language = copy[next] ? next : "en";
    const text = copy[language];
    document.documentElement.lang = language === "zh" ? "zh-CN" : "en";
    document.title = text.title;
    document.querySelector('meta[name="description"]').content = text.description;
    document.querySelectorAll("[data-i18n]").forEach((node) => {
      const value = text[node.dataset.i18n];
      if (value) node.textContent = value;
    });
    document.querySelectorAll("[data-i18n-html]").forEach((node) => {
      const value = text[node.dataset.i18nHtml];
      if (value) node.innerHTML = value;
    });
    document.querySelectorAll("[data-lang]").forEach((button) => {
      const active = button.dataset.lang === language;
      button.classList.toggle("active", active);
      button.setAttribute("aria-pressed", String(active));
    });
    localStorage.setItem("kun-site-language", language);
    if (updateUrl) {
      const url = new URL(location.href);
      url.searchParams.set("lang", language);
      history.replaceState({}, "", url);
    }
  }

  document.querySelectorAll("[data-lang]").forEach((button) => button.addEventListener("click", () => applyLanguage(button.dataset.lang, true)));
  applyLanguage(language);

  const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reducedMotion || !("IntersectionObserver" in window)) {
    document.querySelectorAll(".reveal").forEach((node) => node.classList.add("visible"));
  } else {
    const observer = new IntersectionObserver((entries) => entries.forEach((entry) => {
      if (entry.isIntersecting) { entry.target.classList.add("visible"); observer.unobserve(entry.target); }
    }), { threshold: 0.12 });
    document.querySelectorAll(".reveal").forEach((node) => observer.observe(node));
  }
})();

(() => {
  const cfg = window.KUN_CHAT_CONFIG || {};
  const apiBase = String(cfg.apiBase || "").replace(/\/$/, "");
  const roles = [
    {id:"kunkun",name:"坤坤",real:"蔡徐坤",note:"音乐、舞台与创作",avatar:"./assets/kun-avatar-ai-v1.png",welcome:"你好，我是坤坤。想聊音乐、舞台、创作，或者最近的状态，都可以。"},
    {id:"fengge",name:"峰哥",real:"峰哥",note:"直接、具体的观点",avatar:"./assets/fengge-avatar.jpg",welcome:"有问题就直接问吧。这里会参考已经审核的公开资料来回答。"},
    {id:"linqingxia",name:"青霞",real:"林青霞",note:"电影、阅读与审美",avatar:"./assets/linqingxia-avatar.jpg",welcome:"你好。我们可以聊电影、阅读、写作，也可以聊聊生活里的感受。"},
    {id:"tulei",name:"磊磊",real:"涂磊",note:"关系、责任与边界",avatar:"./assets/tulei-avatar.jpg",welcome:"你可以直接说问题。我们先把事实、责任和边界理清楚。"},
    {id:"laocan",name:"老残",real:"老残",note:"观察、表达与闲聊",avatar:"./assets/laocan-avatar.jpg",welcome:"你好，我是老残，今天有什么想和我聊聊的吗？"}
  ];
  const $ = (id) => document.getElementById(id);
  const state = {persona:"kunkun",histories:{},busy:false,remaining:cfg.freeMessages || 6,audio:null,grant:null,cache:new Map()};
  try { state.histories = JSON.parse(localStorage.getItem("kun-pages-history-v1") || "{}"); } catch {}
  const visitor = localStorage.getItem("kun-pages-visitor") || crypto.randomUUID();
  localStorage.setItem("kun-pages-visitor", visitor);

  function role(){ return roles.find((item)=>item.id===state.persona); }
  function save(){ localStorage.setItem("kun-pages-history-v1", JSON.stringify(state.histories)); }
  function messages(){ return state.histories[state.persona] || []; }
  function setError(text=""){ $("errorBox").hidden=!text; $("errorBox").textContent=text; }
  function stopAudio(){ if(state.audio){state.audio.pause();state.audio.currentTime=0} state.audio=null;state.grant=null;render(); }
  async function request(path, options={}, attempts=3){
    let last;
    for(let i=0;i<attempts;i++){
      try{ const res=await fetch(apiBase+path,options); if(![409,502,503,504].includes(res.status)||i===attempts-1)return res; last=new Error(`HTTP ${res.status}`); }
      catch(error){ last=error;if(i===attempts-1)throw error; }
      await new Promise((resolve)=>setTimeout(resolve,500*(i+1)));
    }
    throw last;
  }
  function renderRoles(){ $("roleList").innerHTML=roles.map((r)=>`<button class="role ${r.id===state.persona?"active":""}" data-role="${r.id}"><img src="${r.avatar}" alt=""><b>${r.name}</b><small>${r.note}</small></button>`).join(""); }
  function escapeHtml(value){ const node=document.createElement("div");node.textContent=value;return node.innerHTML; }
  function render(){
    const r=role(); renderRoles(); $("heroAvatar").src=r.avatar; $("heroName").textContent=r.name; $("heroNote").textContent=`${r.note} · 人格 RAG · 赛博同人`; $("disclosure").textContent=`AI 数字人 / 赛博同人 · 模拟公开表达风格 · 非${r.real}本人或相关团队`; $("quotaButton").textContent=`剩余 ${state.remaining} 次`;
    const list=messages().length?messages():[{role:"assistant",content:r.welcome}];
    $("stream").innerHTML=list.map((m)=>`<article class="message ${m.role}">${m.role==="assistant"?`<img src="${r.avatar}" alt="">`:""}<div class="bubble">${escapeHtml(m.content)}${m.sources?.length?`<div class="sources"><strong>参考公开资料</strong>${m.sources.map((s)=>`<a href="${encodeURI(s.url)}" target="_blank" rel="noreferrer">${escapeHtml(s.title)}</a>`).join("")}</div>`:""}${m.role==="assistant"&&m.audioGrant?`<button class="listen" data-grant="${m.audioGrant}" data-text="${encodeURIComponent(m.content)}">${state.grant===m.audioGrant?"停止播放":"🔊 播放 MiniMax 数字人语音"}</button>`:""}</div></article>`).join("")+(state.busy?`<article class="message assistant"><img src="${r.avatar}" alt=""><div class="bubble">正在组织回答 •••</div></article>`:"");
    $("sendButton").disabled=state.busy||!$("messageInput").value.trim()||state.remaining===0; requestAnimationFrame(()=>$("stream").scrollTo({top:$("stream").scrollHeight,behavior:"smooth"}));
  }
  async function send(){
    const text=$("messageInput").value.trim();if(!text||state.busy)return;setError();$("messageInput").value="";const history=messages().slice(-10);state.histories[state.persona]=[...messages(),{role:"user",content:text}];state.busy=true;render();
    try{const res=await request("/api/chat",{method:"POST",headers:{"content-type":"application/json","x-visitor-id":visitor},body:JSON.stringify({persona:state.persona,message:text,history})});const data=await res.json();if(!res.ok)throw new Error(data.error||"暂时无法回复");state.histories[state.persona].push({role:"assistant",content:data.reply,sources:data.sources||[],audioGrant:data.audioGrant||null});if(typeof data.remaining==="number")state.remaining=data.remaining;save();}
    catch(error){setError(error.message==="Failed to fetch"?"网络未能连接到 API。大陆网络测试阶段可稍后重试；腾讯云函数接入后将切换到国内链路。":(error.message||"网络连接失败"));}finally{state.busy=false;render();}
  }
  async function speak(text,grant){
    if(state.grant===grant&&state.audio&&!state.audio.paused){stopAudio();return}stopAudio();setError();state.grant=grant;render();
    try{let url=state.cache.get(grant);if(!url){const res=await request("/api/synthesize",{method:"POST",headers:{"content-type":"application/json","x-visitor-id":visitor},body:JSON.stringify({persona:state.persona,text,grant})});if(!res.ok){const data=await res.json();throw new Error(data.error||"语音暂不可用")}url=URL.createObjectURL(await res.blob());state.cache.set(grant,url)}const audio=new Audio(url);state.audio=audio;audio.onended=stopAudio;audio.onerror=()=>{stopAudio();setError("音频播放失败，请重试")};await audio.play();}
    catch(error){stopAudio();setError(error.message==="Failed to fetch"?"语音 API 连接失败，请稍后重试。":error.message);}
  }
  $("roleList").addEventListener("click",(e)=>{const button=e.target.closest("[data-role]");if(!button)return;stopAudio();state.persona=button.dataset.role;setError();render();});
  $("composer").addEventListener("submit",(e)=>{e.preventDefault();send()});$("messageInput").addEventListener("input",render);$("messageInput").addEventListener("keydown",(e)=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();send()}});
  $("stream").addEventListener("click",(e)=>{const button=e.target.closest("[data-grant]");if(button)speak(decodeURIComponent(button.dataset.text),button.dataset.grant)});
  $("micButton").addEventListener("click",()=>{const Recognition=window.SpeechRecognition||window.webkitSpeechRecognition;if(!Recognition){setError("当前浏览器不支持网页语音识别，请使用最新版 Chrome、Edge 或 Safari，并允许麦克风权限。");return}const rec=new Recognition();rec.lang="zh-CN";rec.interimResults=true;rec.onstart=()=>$("micButton").classList.add("listening");rec.onend=()=>$("micButton").classList.remove("listening");rec.onerror=()=>setError("没有识别到语音，请检查麦克风权限。");rec.onresult=(event)=>{let text="";for(let i=event.resultIndex;i<event.results.length;i++)text+=event.results[i][0].transcript;$("messageInput").value=text;render()};rec.start()});
  document.addEventListener("click",(e)=>{const opener=e.target.closest("[data-modal]");if(opener)$(opener.dataset.modal).showModal()});document.querySelectorAll(".pack").forEach((button)=>button.addEventListener("click",()=>alert("测试阶段尚未启用真实收款。配置商户号和回调后即可上线。")));
  request("/api/status").then((r)=>r.json()).then((data)=>{$("serviceState").classList.toggle("online",Boolean(data.ready));$("serviceState").lastChild.textContent=data.ready?"文字与数字人语音在线":"服务维护中";if(typeof data.freeMessages==="number")state.remaining=data.freeMessages;render()}).catch(()=>{$("serviceState").lastChild.textContent="API 待切换";render()});
  render();
})();

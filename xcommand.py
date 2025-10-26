# xcommand.py
# Provides a modern UI with both text and voice input.
# Voice uses Web Speech API (webkitSpeechRecognition) in Urdu (ur-PK).
# Flow: user speaks → transcript fills the box → user clicks Send → your /chat does embeddings & answer.
# Includes "Clear Chat" button and a white question area with black text.

UI_HTML = r"""<!doctype html>
<html lang="ur" dir="rtl">
<head>
  <meta charset="utf-8">
  <title>اردو قانونی چیٹ</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">

  <style>
    :root{
      --bg: #0b1220; --panel: #0f172a; --panel-2: #0b1324; --text: #e5e7eb; --muted: #94a3b8;
      --brand: #38bdf8; --brand-2: #22d3ee; --ring: rgba(56,189,248,0.45);
      --bubble-user: #1e293b; --bubble-bot: #0b1931; --ok: #10b981; --warn: #f59e0b; --err: #ef4444;

      /* Question box colors (forced white bg with dark text as requested) */
      --qa-bg: #ffffff;
      --qa-text: #0f172a;
      --qa-border: #d1d5db;
      --qa-placeholder: #6b7280;
    }
    @media (prefers-color-scheme: light){
      :root{
        --bg:#f7fafc; --panel:#ffffff; --panel-2:#f1f5f9; --text:#0f172a; --muted:#475569;
        --brand:#0284c7; --brand-2:#06b6d4; --ring: rgba(2,132,199,0.25);
        --bubble-user:#e2e8f0; --bubble-bot:#e0f2fe;
      }
    }
    *{box-sizing:border-box}
    html,body{height:100%}
    body{
      margin:0; background: radial-gradient(1200px 800px at 90% -10%, #0ea5e933 0%, transparent 60%),
                           radial-gradient(1000px 700px at -10% 110%, #22d3ee22 0%, transparent 60%), var(--bg);
      color:var(--text);
      font:16px/1.7 system-ui, -apple-system, "Segoe UI", Roboto, "Noto Naskh Arabic", Arial, sans-serif;
    }
    .wrap{max-width:980px; margin:24px auto; padding:0 12px;}
    .card{background:linear-gradient(180deg, var(--panel), var(--panel-2));
      border:1px solid #ffffff10; border-radius:20px; overflow:hidden;
      box-shadow:0 10px 30px rgba(0,0,0,.25), inset 0 1px 0 rgba(255,255,255,.04);
    }
    .hdr{display:flex; align-items:center; justify-content:space-between; padding:16px 18px; border-bottom:1px solid #ffffff14;}
    .title{font-weight:700; font-size:18px}
    .sub{color:var(--muted); font-size:13px}
    .status{font-size:12px; padding:6px 10px; border-radius:999px; background:#0f1b33; border:1px solid #1e3a8a33}
    .scroll{height:min(62vh,560px); overflow:auto; padding:18px;}
    .msg{display:flex; gap:12px; margin:14px 0; align-items:flex-start}
    .avatar{width:32px; height:32px; border-radius:10px; flex:0 0 auto; display:grid; place-items:center; color:#cbd5e1; font-weight:700; font-size:12px; background:#172554}
    .bubble{padding:12px 14px; border-radius:14px; max-width:85%; border:1px solid #ffffff10; white-space:pre-wrap}
    .user .bubble{background:var(--bubble-user)}
    .bot .bubble{background:var(--bubble-bot)}
    .copy{font-size:11px; color:var(--muted); cursor:pointer; user-select:none; margin-top:8px}
    .sugg{display:flex; flex-wrap:wrap; gap:8px; padding:10px 18px 0 18px}
    .sugg button{background:#0f1b33; border:1px solid #1e3a8a33; color:var(--text); font-size:13px; padding:8px 12px; border-radius:12px; cursor:pointer}
    .bar{color:var(--muted); font-size:13px; padding:0 18px 10px 18px}
    .ftr{border-top:1px solid #ffffff14; padding:14px 16px}

    .composer{
      display:flex; gap:8px; align-items:flex-end;
      border:1px solid #ffffff1a; border-radius:16px; padding:8px;
      background: #0b1220aa; box-shadow:0 0 0 0 var(--ring)
    }
    .composer:focus-within{ box-shadow:0 0 0 4px var(--ring) }

    /* QUESTION AREA — white background and black text */
    textarea#input{
      flex:1; resize:none; min-height:50px; max-height:160px; width:100%;
      border:1px solid var(--qa-border);
      outline:0;
      background:var(--qa-bg) !important;  /* white */
      color:var(--qa-text) !important;      /* black/dark */
      border-radius:12px;
      font:16px/1.7 inherit; padding:10px 12px;
      box-shadow: inset 0 1px 0 rgba(0,0,0,.02);
    }
    textarea#input::placeholder{ color: var(--qa-placeholder); opacity: 1; }
    textarea#input:focus{ box-shadow: 0 0 0 3px rgba(56,189,248,.25); border-color:#93c5fd; }

    .btn{
      flex:0 0 auto; padding:12px 16px; border:0; border-radius:12px; cursor:pointer; font-weight:600; color:#0b1220;
      background:linear-gradient(180deg, var(--brand), var(--brand-2)); box-shadow:0 8px 18px rgba(56,189,248,.35)
    }
    .btn[disabled]{opacity:.6; cursor:not-allowed; box-shadow:none}

    .btn-ghost{
      flex:0 0 auto;
      padding:12px 14px; border-radius:12px; cursor:pointer; font-weight:600;
      background: transparent; color: var(--text); border:1px solid #ffffff22;
    }
    .btn-ghost:hover{ background:#0b1b33; }

    .mic{
      flex:0 0 auto; border:1px solid #ffffff22; background:#0b1b33; color:#e5e7eb; border-radius:12px;
      padding:10px 12px; cursor:pointer; display:inline-flex; align-items:center; gap:8px; min-width:120px; justify-content:center
    }
    .mic.rec{border-color: #ef4444aa; box-shadow: 0 0 0 3px rgba(239,68,68,.25) inset}
    .dot{width:10px; height:10px; border-radius:50%}
    .dot.idle{background:#64748b}
    .dot.listening{background:#ef4444; animation: blink 1s infinite}
    @keyframes blink{0%,100%{opacity:1} 50%{opacity:0.25}}
    .hint{font-size:12px; color:var(--muted); padding-top:6px}

    /* 🔧 HOTFIX: enforce readable text colors on all common elements */
    body, .bubble, .title, .sub, .status,
    button, .btn, .btn-ghost, .mic, .sugg button,
    input, select {
      color: var(--text) !important;
    }
    /* Keep main action button text dark on bright gradient */
    .btn { color: #0b1220 !important; }
    .mic { color: #e5e7eb !important; }

    ::selection { background: rgba(56,189,248,.35); color: #0b1220; }

    /* Autofill and caret colors */
    textarea, input { caret-color: var(--brand); }
    input:-webkit-autofill,
    input:-webkit-autofill:hover,
    input:-webkit-autofill:focus {
      -webkit-text-fill-color: var(--text) !important;
      -webkit-box-shadow: 0 0 0px 1000px transparent inset !important;
      box-shadow: 0 0 0px 1000px transparent inset !important;
    }

    :root { color-scheme: dark light; }
  </style>
  <!-- 🔧 HOTFIX: enforce readable text colors on dark and light backgrounds -->
<style>
  /* make sure all common controls inherit our readable text color */
  body, .bubble, .title, .sub, .status,
  button, .btn, .mic, .sugg button,
  textarea, input, select {
    color: var(--text) !important;
  }

  /* explicit colors for the two main buttons */
  .btn { color: #0b1220 !important; }            /* bright gradient background → dark text */
  .mic { color: #e5e7eb !important; }            /* dark button → light text */

  /* placeholders visible on dark */
  ::placeholder { color: #cbd5e1 !important; opacity: 1; }
  textarea::placeholder, input::placeholder { color: #cbd5e1 !important; opacity: 1; }

  /* selection highlight */
  ::selection { background: rgba(56,189,248,.35); color: #0b1220; }

  /* ensure bubbles always use readable color */
  .user .bubble, .bot .bubble { color: var(--text) !important; }

  /* status chip text visibility */
  .status { color: var(--text) !important; }

  /* suggestion pills: light text on dark pill */
  .sugg button { color: #e5e7eb !important; }

  /* input caret and autofill (chromium) */
  textarea, input {
    caret-color: var(--brand);
    -webkit-text-fill-color: var(--text);
  }
  input:-webkit-autofill,
  input:-webkit-autofill:hover,
  input:-webkit-autofill:focus {
    -webkit-text-fill-color: var(--text) !important;
    -webkit-box-shadow: 0 0 0px 1000px transparent inset !important;
    box-shadow: 0 0 0px 1000px transparent inset !important;
  }

  /* for users with "force dark mode" extensions: prevent surprise inversions */
  :root { color-scheme: dark light; }
</style>

</head>
<body>
  <div class="wrap">
    <div class="card">
      <div class="hdr">
        <div>
          <div class="title">اردو قانونی چیٹ</div>
          <div class="sub">ٹیکسٹ یا آواز — جواب ہمیشہ ۲–۳ جملوں میں</div>
        </div>
        <div id="status" class="status">تیار</div>
      </div>

      <div class="sugg" id="suggestions">
        <button data-q="غیر قانونی گرفتاری کو کیسے چیلنج کروں؟">غیر قانونی گرفتاری کو کیسے چیلنج کروں؟</button>
        <button data-q="ہائی کورٹ میں حبسِ جسم کی درخواست کا طریقہ کیا ہے؟">حبسِ جسم کی درخواست</button>
        <button data-q="وارنٹ کے بغیر گرفتاری ہو تو کیا حق حاصل ہیں؟">وارنٹ کے بغیر گرفتاری</button>
        <button data-q="ضمانت کے لیے کون سے کاغذات درکار ہوتے ہیں؟">ضمانت کے کاغذات</button>
      </div>
      <div class="bar">Shift+Enter نئی سطر؛ Enter بھیجنے کیلئے</div>

      <div id="chat" class="scroll" aria-live="polite"></div>

      <div class="ftr">
        <div class="composer" id="composer">
          <textarea id="input" placeholder="اپنا سوال یہاں لکھیں…"></textarea>

          <!-- Voice button -->
          <button id="micBtn" class="mic" type="button">
            <span class="dot idle" id="micDot"></span>
            <span id="micLabel">آواز سے لکھیں</span>
          </button>

          <button class="btn" id="send" type="button">بھیجیں ↵</button>
          <button class="btn-ghost" id="clear" type="button" title="گفتگو صاف کریں">خالی کریں</button>
        </div>
        <div class="hint">آواز سے لکھنے کیلئے مائیک کی اجازت دیں۔ خاموشی پر ریکارڈنگ خود بخود بند ہوگی، متن اوپر باکس میں آ جائے گا—پھر "بھیجیں" دبائیں۔</div>
      </div>
    </div>
  </div>

  <script>
    const el = (s, r=document)=>r.querySelector(s);
    const chat = el('#chat');
    const input = el('#input');
    const sendBtn = el('#send');
    const clearBtn = el('#clear');
    const micBtn = el('#micBtn');
    const micDot = el('#micDot');
    const micLabel = el('#micLabel');
    const status = el('#status');
    const suggestions = el('#suggestions');

    const state = {
      busy:false,
      recognizing:false,
      history: JSON.parse(localStorage.getItem('urdu-law-chat') || '[]')
    };

    function save(){ localStorage.setItem('urdu-law-chat', JSON.stringify(state.history)); }

    function bubble(role, text){
      const row = document.createElement('div'); row.className = 'msg ' + role;
      const av = document.createElement('div'); av.className = 'avatar'; av.textContent = role==='user'?'آپ':'AI';
      const body = document.createElement('div'); body.className = 'bubble'; body.textContent = text;
      row.appendChild(av); row.appendChild(body);

      if(role==='bot'){
        const cp = document.createElement('div'); cp.className='copy'; cp.textContent='کاپی کریں';
        cp.onclick = async ()=>{ try{ await navigator.clipboard.writeText(text); cp.textContent='کاپی ہوگئی ✓'; setTimeout(()=>cp.textContent='کاپی کریں',1200);}catch{} };
        row.appendChild(cp);
      }
      chat.appendChild(row);
      chat.scrollTop = chat.scrollHeight;
    }

    function renderFromStorage(){
      chat.innerHTML='';
      state.history.forEach(m=>bubble(m.role,m.text));
    }
    renderFromStorage();

    // textarea autosize
    input.addEventListener('input', ()=>{
      input.style.height='auto';
      input.style.height=Math.min(input.scrollHeight,160)+'px';
    });

    // Enter to send, Shift+Enter newline
    input.addEventListener('keydown', (e)=>{
      if(e.key==='Enter' && !e.shiftKey){ e.preventDefault(); send(); }
    });

    // Suggestions
    suggestions.addEventListener('click', (e)=>{
      if(e.target.tagName==='BUTTON'){ input.value = e.target.getAttribute('data-q'); input.focus(); input.dispatchEvent(new Event('input')); }
    });

    // Clear Chat
    clearBtn.addEventListener('click', ()=>{
      state.history = [];
      save();
      renderFromStorage();
      setStatus('گفتگو خالی کر دی گئی');
    });

    async function send(){
      const text = input.value.trim();
      if(!text || state.busy) return;

      state.busy = true; sendBtn.disabled = true; setStatus('بھیج رہے ہیں…');
      bubble('user', text); state.history.push({role:'user', text}); save();
      input.value=''; input.style.height='50px';

      const typing = document.createElement('div'); typing.className='msg bot';
      typing.innerHTML = '<div class="avatar">AI</div><div class="bubble">لکھا جا رہا ہے…</div>';
      chat.appendChild(typing); chat.scrollTop = chat.scrollHeight;

      try{
        const res = await fetch('/chat', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({message:text})});
        const data = await res.json();
        typing.remove();
        const ans = data.answer || 'کوئی جواب دستیاب نہیں۔';
        bubble('bot', ans); state.history.push({role:'bot', text:ans}); save();
        setStatus('تیار');
      }catch{
        typing.remove();
        bubble('bot', 'سرور سے رابطہ نہیں ہو سکا۔ براہِ کرم دوبارہ کوشش کریں۔');
        setStatus('خرابی');
      }finally{
        state.busy = false; sendBtn.disabled = false;
      }
    }
    sendBtn.addEventListener('click', send);

    function setStatus(t){ status.textContent = t; }

    // -------- Voice (Urdu) with Web Speech API ----------
    let recognizer = null;
    let mediaStream = null;

    function supported(){
      return ('webkitSpeechRecognition' in window) || ('SpeechRecognition' in window);
    }

    async function ensureAudioStream(){
      try{
        if (!mediaStream) {
          mediaStream = await navigator.mediaDevices.getUserMedia({
            audio: {
              channelCount: 1,
              sampleRate: 44100,
              echoCancellation: true,
              noiseSuppression: true,
              autoGainControl: true
            }
          });
        }
      }catch(err){
        console.warn('Mic permission / constraints error:', err);
      }
    }

    async function toggleVoice(){
      if(!supported()){
        alert('آپ کے براؤزر میں آواز کی پہچان دستیاب نہیں۔ براہِ کرم Chrome/Edge استعمال کریں۔');
        return;
      }
      if(state.recognizing){ stopVoice(); return; }

      await ensureAudioStream();
      startVoice();
    }

    function startVoice(){
      const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
      recognizer = new SR();
      recognizer.lang = 'ur-PK'; // Urdu (Pakistan)
      recognizer.interimResults = true;
      recognizer.maxAlternatives = 1;
      recognizer.continuous = true;

      let finalText = '';

      recognizer.onstart = ()=>{
        state.recognizing = true;
        micBtn.classList.add('rec');
        micDot.className = 'dot listening';
        micLabel.textContent = 'سُن رہا ہے…';
        setStatus('بولیں…');
        input.placeholder = 'بولیں… خاموشی پر خود رُک جائے گا';
      };

      recognizer.onresult = (e)=>{
        let interim = '';
        for(let i=e.resultIndex; i<e.results.length; i++){
          const t = e.results[i][0].transcript;
          if(e.results[i].isFinal){ finalText += t + ' '; }
          else { interim += t; }
        }
        const combined = (finalText + ' ' + interim).trim();
        input.value = combined;
        input.dispatchEvent(new Event('input')); // autosize
      };

      recognizer.onerror = (e)=>{
        console.warn('speech error:', e.error);
        setStatus('آواز میں خرابی');
        stopVoice(true);
      };

      recognizer.onend = ()=>{
        // Auto-stop when silence
        stopVoice();
        if(input.value.trim()){
          setStatus('متن تیار — بھیجنے کیلئے کلک کریں');
        }else{
          setStatus('تیار');
        }
      };

      try{ recognizer.start(); } catch(e){ /* ignore double start */ }
    }

    function stopVoice(silent){
      if(recognizer){
        try{ recognizer.stop(); }catch{}
        recognizer = null;
      }
      state.recognizing = false;
      micBtn.classList.remove('rec');
      micDot.className = 'dot idle';
      micLabel.textContent = 'آواز سے لکھیں';
      if(!silent) input.placeholder = 'اپنا سوال یہاں لکھیں…';
      if(mediaStream){
        mediaStream.getTracks().forEach(t=>t.stop());
        mediaStream = null;
      }
    }

    micBtn.addEventListener('click', toggleVoice);
  </script>
</body>
</html>
"""

(function () {
  // 1. Find the current script tag to extract configuration attributes
  const scriptTag = document.currentScript || document.querySelector('script[data-chatbot-id]');

  const chatbotId = scriptTag.getAttribute('data-chatbot-id');
  if (!chatbotId) {
    console.error('BlinkBot Widget Error: data-chatbot-id attribute is missing.');
    return;
  }

  // Configurations with local development fallbacks
  const apiUrl = scriptTag.getAttribute('data-api-url')
  const supabaseUrl = scriptTag.getAttribute('data-supabase-url')
  const supabaseKey = scriptTag.getAttribute('data-supabase-key');

  // Default Chatbot styling settings
  let botSettings = {
    name: 'BlinkBot Assistant',
    themeColor: '#4f46e5',
    welcomeMessage: 'Hi there! How can I help you today?',
    position: 'bottom-right',
    avatar: '🤖',
    borderRadius: 'rounded',
    fontFamily: 'system-ui'
  };

  let chatHistory = [];
  let isOpen = false;
  let currentLanguage = 'en';

  const LANGUAGES = [
    { id: "en", name: "EN" },
    { id: "es", name: "ES" },
    { id: "fr", name: "FR" },
    { id: "de", name: "DE" },
    { id: "hi", name: "HI" },
    { id: "zh-CN", name: "ZH" },
    { id: "ja", name: "JA" },
    { id: "ko", name: "KO" },
  ];

  // 2. Fetch Chatbot Config from Supabase
  async function fetchConfig() {
    try {
      const response = await fetch(`${supabaseUrl}/rest/v1/chatbots?id=eq.${chatbotId}&select=*`, {
        cache: 'no-store',
        headers: {
          'apikey': supabaseKey,
          'Authorization': `Bearer ${supabaseKey}`
        }
      });
      if (response.ok) {
        const data = await response.json();
        if (data && data.length > 0) {
          const bot = data[0];
          botSettings.name = bot.name || botSettings.name;
          
          let parsedSettings = bot.settings;
          if (typeof parsedSettings === 'string') {
            try { parsedSettings = JSON.parse(parsedSettings); } catch (e) {}
          }
          
          if (parsedSettings) {
            botSettings.themeColor = parsedSettings.themeColor || botSettings.themeColor;
            botSettings.welcomeMessage = parsedSettings.welcomeMessage || botSettings.welcomeMessage;
            botSettings.position = parsedSettings.position || botSettings.position;
            botSettings.avatar = parsedSettings.avatar || botSettings.avatar;
            botSettings.borderRadius = parsedSettings.borderRadius || botSettings.borderRadius;
            botSettings.fontFamily = parsedSettings.fontFamily || botSettings.fontFamily;
          }
        }
      }
    } catch (err) {
      console.warn('BlinkBot Widget: Failed to fetch settings from Supabase, using defaults.', err);
    }
  }

  // 3. Inject CSS styles dynamically
  function injectStyles() {
    const styleEl = document.createElement('style');
    styleEl.innerHTML = `
      #blinkbot-bubble {
        position: fixed;
        bottom: 30px;
        width: 60px;
        height: 60px;
        border-radius: ${botSettings.borderRadius === 'square' ? '0' : botSettings.borderRadius === 'pill' ? '20px' : '50%'};
        color: white;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 8px 24px rgba(0,0,0,0.2);
        z-index: 2147483640;
        transition: transform 0.2s ease, opacity 0.2s ease;
      }
      #blinkbot-bubble:hover {
        transform: scale(1.08);
      }
      #blinkbot-bubble.bottom-right {
        right: 30px;
      }
      #blinkbot-bubble.bottom-left {
        left: 30px;
      }
      #blinkbot-bubble svg {
        width: 28px;
        height: 28px;
        fill: none;
        stroke: currentColor;
        stroke-width: 2;
        stroke-linecap: round;
        stroke-linejoin: round;
      }
      #blinkbot-window {
        position: fixed;
        bottom: 105px;
        width: 380px;
        height: 580px;
        max-height: calc(100vh - 140px);
        max-width: calc(100vw - 60px);
        background: rgba(255, 255, 255, 0.3);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: ${botSettings.borderRadius === 'square' ? '0' : botSettings.borderRadius === 'pill' ? '24px' : '16px'};
        box-shadow: 0 12px 36px rgba(0,0,0,0.15);
        display: none;
        flex-direction: column;
        overflow: hidden;
        z-index: 2147483641;
        font-family: ${botSettings.fontFamily === 'system-ui' ? '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif' : botSettings.fontFamily + ', sans-serif'};
      }
      #blinkbot-window.bottom-right {
        right: 30px;
      }
      #blinkbot-window.bottom-left {
        left: 30px;
      }
      #blinkbot-window.open {
        display: flex;
      }
      .rm-header {
        color: white;
        padding: 16px 20px;
        display: flex;
        align-items: center;
        justify-content: space-between;
      }
      .rm-header h4 {
        margin: 0;
        font-size: 1rem;
        font-weight: 600;
      }
      .rm-header p {
        margin: 2px 0 0 0;
        font-size: 0.75rem;
        opacity: 0.8;
      }
      .rm-close {
        background: none;
        border: none;
        color: white;
        font-size: 1.5rem;
        cursor: pointer;
        opacity: 0.8;
        padding: 0;
        line-height: 1;
      }
      .rm-close:hover {
        opacity: 1;
      }
      .rm-lang-select {
        background: rgba(255, 255, 255, 0.1);
        color: white;
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 6px;
        padding: 4px;
        font-size: 0.75rem;
        cursor: pointer;
        outline: none;
        margin-right: 12px;
      }
      .rm-lang-select option {
        background: #1e293b;
        color: white;
      }
      .rm-messages {
        flex: 1;
        overflow-y: auto;
        padding: 20px;
        display: flex;
        flex-direction: column;
        gap: 12px;
        background: transparent;
      }
      .rm-msg {
        max-width: 80%;
        padding: 10px 14px;
        border-radius: ${botSettings.borderRadius === 'square' ? '0' : '12px'};
        font-size: 0.9rem;
        line-height: 1.4;
        word-wrap: break-word;
      }
      .rm-msg.user {
        align-self: flex-end;
        color: white;
        border-bottom-right-radius: 2px;
      }
      .rm-msg.bot {
        align-self: flex-start;
        background: #e2e8f0;
        color: #1e293b;
        border-bottom-left-radius: 2px;
      }
      .rm-input-area {
        padding: 12px 16px;
        background: rgba(255, 255, 255, 0.5);
        border-top: 1px solid rgba(255, 255, 255, 0.2);
        display: flex;
        gap: 8px;
        align-items: center;
      }
      .rm-input {
        flex: 1;
        border: 1px solid #cbd5e1;
        border-radius: ${botSettings.borderRadius === 'square' ? '0' : botSettings.borderRadius === 'pill' ? '9999px' : '8px'};
        padding: 10px 12px;
        font-size: 0.9rem;
        outline: none;
      }
      .rm-input:focus {
        border-color: #94a3b8;
      }
      .rm-send {
        border: none;
        color: white;
        border-radius: 8px;
        width: 38px;
        height: 38px;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
      }
      .rm-send svg {
        width: 16px;
        height: 16px;
        fill: none;
        stroke: currentColor;
        stroke-width: 2;
        stroke-linecap: round;
        stroke-linejoin: round;
      }
      .rm-brand {
        text-align: center;
        font-size: 10px;
        color: #94a3b8;
        margin-top: 4px;
      }
      .rm-typing {
        display: flex;
        gap: 4px;
        align-items: center;
        padding: 4px 8px;
      }
      .rm-dot {
        width: 5px;
        height: 5px;
        background: #64748b;
        border-radius: 50%;
        animation: rm-bounce 1.4s infinite ease-in-out both;
      }
      .rm-dot:nth-child(1) { animation-delay: -0.32s; }
      .rm-dot:nth-child(2) { animation-delay: -0.16s; }
      @keyframes rm-bounce {
        0%, 80%, 100% { transform: scale(0); }
        40% { transform: scale(1.0); }
      }
      .rm-mic {
        border: none;
        background: transparent;
        color: #64748b;
        width: 38px;
        height: 38px;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        transition: color 0.2s;
      }
      .rm-mic:hover { color: #334155; }
      .rm-mic.recording { color: #ef4444; animation: rm-pulse 1.5s infinite; }
      @keyframes rm-pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }

      .rm-tts {
        border: none;
        background: transparent;
        color: #94a3b8;
        cursor: pointer;
        padding: 4px;
        margin-top: 6px;
        display: inline-flex;
        align-items: center;
        border-radius: 4px;
      }
      .rm-tts:hover { color: #64748b; background: rgba(0,0,0,0.05); }
    `;
    document.head.appendChild(styleEl);
  }

  // 4. Create and inject HTML elements
  function injectHTML() {
    // Bubble Trigger
    const bubble = document.createElement('div');
    bubble.id = 'blinkbot-bubble';
    bubble.style.backgroundColor = botSettings.themeColor;
    bubble.className = botSettings.position;
    bubble.innerHTML = botSettings.avatar && botSettings.avatar !== "🤖" ? `<span style="font-size: 24px;">${botSettings.avatar}</span>` : `
      <svg viewBox="0 0 24 24">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
      </svg>
    `;
    bubble.onclick = toggleChat;
    document.body.appendChild(bubble);

    // Chat Window
    const windowDiv = document.createElement('div');
    windowDiv.id = 'blinkbot-window';
    windowDiv.className = `${botSettings.position}`;
    windowDiv.innerHTML = `
      <div class="rm-header" style="background-color: ${botSettings.themeColor}">
        <div style="display: flex; gap: 12px; align-items: center;">
          <div style="width: 32px; height: 32px; border-radius: 50%; background: rgba(255,255,255,0.2); display: flex; align-items: center; justify-content: center; font-size: 16px;">
            ${botSettings.avatar || '🤖'}
          </div>
          <div>
            <h4>${botSettings.name}</h4>
            <p>Online | Powered by BlinkBot</p>
          </div>
        </div>
        <div style="display: flex; align-items: center;">
          <select id="blinkbot-lang-select" class="rm-lang-select" title="Select STT/TTS Language">
            ${LANGUAGES.map(l => `<option value="${l.id}">${l.name}</option>`).join('')}
          </select>
          <button class="rm-close" id="blinkbot-close-btn">&times;</button>
        </div>
      </div>
      <div class="rm-messages" id="blinkbot-messages">
        <div class="rm-msg bot">${botSettings.welcomeMessage}</div>
      </div>
      <div style="background: transparent;">
        <div class="rm-input-area">
          <input type="text" class="rm-input" id="blinkbot-input" placeholder="Ask a question...">
          <button class="rm-mic" id="blinkbot-mic-btn" title="Start recording">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><line x1="12" y1="19" x2="12" y2="23"></line><line x1="8" y1="23" x2="16" y2="23"></line></svg>
          </button>
          <button class="rm-send" id="blinkbot-send-btn" style="background-color: ${botSettings.themeColor}">
            <svg viewBox="0 0 24 24">
              <line x1="22" y1="2" x2="11" y2="13"></line>
              <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
            </svg>
          </button>
        </div>
        <div class="rm-brand">Powered by BlinkBot</div>
      </div>
    `;

    document.body.appendChild(windowDiv);

    // Add event listeners
    document.getElementById('blinkbot-close-btn').onclick = toggleChat;
    document.getElementById('blinkbot-send-btn').onclick = handleSend;
    document.getElementById('blinkbot-mic-btn').onclick = toggleMic;
    document.getElementById('blinkbot-input').onkeypress = function (e) {
      if (e.key === 'Enter') handleSend();
    };
    document.getElementById('blinkbot-lang-select').onchange = function (e) {
      currentLanguage = e.target.value;
    };
  }

  let mediaRecorder = null;
  let audioChunks = [];
  let isRecording = false;

  async function toggleMic() {
    const micBtn = document.getElementById('blinkbot-mic-btn');
    const inputEl = document.getElementById('blinkbot-input');

    if (isRecording) {
      if (mediaRecorder) {
        mediaRecorder.stop();
        mediaRecorder.stream.getTracks().forEach(t => t.stop());
      }
      isRecording = false;
      micBtn.classList.remove('recording');
      micBtn.innerHTML = '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><line x1="12" y1="19" x2="12" y2="23"></line><line x1="8" y1="23" x2="16" y2="23"></line></svg>';
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder = new MediaRecorder(stream);
      audioChunks = [];

      mediaRecorder.ondataavailable = e => {
        if (e.data.size > 0) audioChunks.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
        const formData = new FormData();
        formData.append("file", audioBlob, "recording.webm");
        formData.append("language", currentLanguage);

        try {
          const response = await fetch(`${apiUrl}/stt`, {
            method: "POST",
            body: formData,
          });
          if (response.ok) {
            const data = await response.json();
            inputEl.value = inputEl.value + (inputEl.value ? " " : "") + data.text;
          } else {
            console.error("STT Error:", await response.text());
          }
        } catch (err) {
          console.error("Error sending audio:", err);
        }
      };

      mediaRecorder.start();
      isRecording = true;
      micBtn.classList.add('recording');
      micBtn.innerHTML = '<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" stroke="none"><rect x="6" y="6" width="12" height="12"></rect></svg>';
    } catch (err) {
      console.error("Error accessing mic:", err);
    }
  }

  function toggleChat() {
    isOpen = !isOpen;
    const windowEl = document.getElementById('blinkbot-window');
    if (isOpen) {
      windowEl.classList.add('open');
      document.getElementById('blinkbot-input').focus();
    } else {
      windowEl.classList.remove('open');
    }
  }

  // Basic formatting helper (bold, code, simple line breaks)
  function formatText(text) {
    let clean = text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    clean = clean.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    clean = clean.replace(/`(.*?)`/g, '<code>$1</code>');
    return clean.split('\n').join('<br>');
  }

  let currentAudio = null;
  let isSpeaking = false;

  function addTTSButton(container, text) {
    const ttsBtn = document.createElement('button');
    ttsBtn.className = 'rm-tts';
    ttsBtn.title = "Read aloud";
    ttsBtn.innerHTML = '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path></svg>';
    
    ttsBtn.onclick = async () => {
      if (isSpeaking) {
        if (currentAudio) {
          currentAudio.pause();
          currentAudio.src = "";
        }
        isSpeaking = false;
        ttsBtn.innerHTML = '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path></svg>';
        return;
      }

      const cleanText = text
        .replace(/!\[.*?\]\(.*?\)/g, '')
        .replace(/\[(.*?)\]\(.*?\)/g, '$1')
        .replace(/[*_~`#>-]/g, ' ')
        .trim();

      if (!cleanText) return;

      try {
        isSpeaking = true;
        ttsBtn.innerHTML = '<svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor" stroke="none"><rect x="6" y="6" width="12" height="12"></rect></svg>';

        const response = await fetch(`${apiUrl}/api/tts`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            text: cleanText,
            language: currentLanguage
          })
        });

        if (!response.ok) throw new Error("TTS failed");

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        
        currentAudio = new Audio(url);
        currentAudio.onended = () => {
          isSpeaking = false;
          ttsBtn.innerHTML = '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path></svg>';
          URL.revokeObjectURL(url);
        };
        
        currentAudio.play();
      } catch (err) {
        console.error("TTS Error:", err);
        isSpeaking = false;
        ttsBtn.innerHTML = '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path></svg>';
      }
    };

    const flexDiv = document.createElement('div');
    flexDiv.style.marginTop = '4px';
    flexDiv.appendChild(ttsBtn);
    container.appendChild(flexDiv);
  }


  let ws = null;
  let clientId = Math.random().toString(36).substring(7);

  function getWsUrl() {
    let base = apiUrl.replace('http://', 'ws://').replace('https://', 'wss://');
    return `${base}/ws/widget/chat/${clientId}`;
  }

  function ensureWsConnection() {
    return new Promise((resolve, reject) => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        resolve();
        return;
      }
      ws = new WebSocket(getWsUrl());
      ws.onopen = () => {
        console.log("BlinkBot Widget WS Connected");
        resolve();
      };
      ws.onerror = (err) => {
        reject(err);
      };
      // Note: Reconnect logic could be added here
    });
  }

  async function handleSend() {
    const inputEl = document.getElementById('blinkbot-input');
    const text = inputEl.value.trim();
    if (!text) return;

    inputEl.value = '';

    const messagesEl = document.getElementById('blinkbot-messages');

    // 1. Append User Message
    const userMsg = document.createElement('div');
    userMsg.className = 'rm-msg user';
    userMsg.style.backgroundColor = botSettings.themeColor;
    userMsg.textContent = text;
    messagesEl.appendChild(userMsg);
    messagesEl.scrollTop = messagesEl.scrollHeight;

    // 2. Append Typing/Bot container
    const botMsg = document.createElement('div');
    botMsg.className = 'rm-msg bot';
    
    const typing = document.createElement('div');
    typing.className = 'rm-typing';
    typing.innerHTML = '<span class="rm-dot"></span><span class="rm-dot"></span><span class="rm-dot"></span>';
    botMsg.appendChild(typing);
    messagesEl.appendChild(botMsg);
    messagesEl.scrollTop = messagesEl.scrollHeight;

    try {
      await ensureWsConnection();

      let streamedResponse = '';
      
      const onMessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'text_chunk') {
            if (streamedResponse === '') {
              botMsg.innerHTML = '';
            }
            streamedResponse += data.content;
            botMsg.innerHTML = formatText(streamedResponse);
            messagesEl.scrollTop = messagesEl.scrollHeight;
          } else if (data.type === 'error') {
            botMsg.innerHTML = `<span style="color: #ef4444;">Error: ${data.content}</span>`;
            ws.removeEventListener('message', onMessage);
          } else if (data.type === 'stream_end') {
            chatHistory.push({ role: 'user', content: text });
            chatHistory.push({ role: 'assistant', content: streamedResponse });
            addTTSButton(botMsg, streamedResponse);
            messagesEl.scrollTop = messagesEl.scrollHeight;
            ws.removeEventListener('message', onMessage);
          }
        } catch (e) {
          console.error("Parse error", e);
        }
      };

      ws.addEventListener('message', onMessage);

      ws.send(JSON.stringify({
        type: 'chat_request',
        payload: {
          chatbot_id: chatbotId,
          message: text,
          history: chatHistory,
          language: currentLanguage
        }
      }));

    } catch (err) {
      botMsg.innerHTML = `<span style="color: #ef4444;">Error: ${err.message}</span>`;
      messagesEl.scrollTop = messagesEl.scrollHeight;
    }
  }

  // Initialization lifecycle
  async function init() {
    await fetchConfig();
    injectStyles();
    injectHTML();
  }

  if (document.readyState === 'complete' || document.readyState === 'interactive') {
    init();
  } else {
    window.addEventListener('DOMContentLoaded', init);
  }
})();

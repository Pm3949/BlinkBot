(function () {
  // 1. Find the current script tag to extract configuration attributes
  const scriptTag = document.currentScript || document.querySelector('script[data-chatbot-id]');

  const chatbotId = scriptTag.getAttribute('data-chatbot-id');
  if (!chatbotId) {
    console.error('BlinkBot Widget Error: data-chatbot-id attribute is missing.');
    return;
  }

  // Configurations with local development fallbacks[cite: 1]
  const apiUrl = scriptTag.getAttribute('data-api-url');
  const supabaseUrl = scriptTag.getAttribute('data-supabase-url');
  const supabaseKey = scriptTag.getAttribute('data-supabase-key');

  // Default Chatbot styling settings[cite: 1]
  let botSettings = {
    name: 'BlinkBot Assistant',
    themeColor: '#4f46e5',
    welcomeMessage: 'Hi there! How can I help you today?',
    position: 'bottom-right',
    avatar: '🤖',
    borderRadius: 'rounded',
    fontFamily: 'system-ui'
  };

  const isUrl = (str) => {
    if (!str) return false;
    if (str.startsWith('http://') || str.startsWith('https://') || str.startsWith('/') || str.startsWith('data:image/')) return true;
    if (str.includes('.') && (str.endsWith('.png') || str.endsWith('.jpg') || str.endsWith('.jpeg') || str.endsWith('.svg') || str.endsWith('.gif') || str.includes('/'))) return true;
    return false;
  };

  const getImageUrl = (str) => {
    if (!str) return "";
    if (str.startsWith('http://') || str.startsWith('https://') || str.startsWith('/') || str.startsWith('data:image/')) return str;
    return 'https://' + str;
  };

  const getAvatarHTML = (avatarStr, size = "24px") => {
    if (isUrl(avatarStr)) {
      return `<img src="${getImageUrl(avatarStr)}" style="width: ${size}; height: ${size}; border-radius: 50%; object-fit: cover; display: block;" alt="Avatar" />`;
    }
    return `<span style="font-size: ${size};">${avatarStr || '🤖'}</span>`;
  };

  let chatHistory = [];
  let isOpen = false;
  let currentLanguage = 'en';
  let isInitializing = true; // Added to track loading state

  const LANGUAGES = [
    { id: "en", name: "EN" }, { id: "es", name: "ES" }, { id: "fr", name: "FR" },
    { id: "de", name: "DE" }, { id: "hi", name: "HI" }, { id: "zh-CN", name: "ZH" },
    { id: "ja", name: "JA" }, { id: "ko", name: "KO" },
  ];

  // 2. Fetch Chatbot Config from API[cite: 1]
  async function fetchConfig() {
    try {
      const response = await fetch(`${apiUrl}/api/chatbots/${chatbotId}`, { cache: 'no-store' });
      if (response.ok) {
        const bot = await response.json();
        if (bot) {
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
      console.warn('BlinkBot Widget: Failed to fetch settings, using defaults.', err);
    }
  }

  // 3. Inject CSS styles dynamically with improved UI[cite: 1]
  function injectStyles() {
    const styleEl = document.createElement('style');
    styleEl.innerHTML = `
      #blinkbot-bubble {
        position: fixed;
        bottom: 30px;
        width: 64px;
        height: 64px;
        border-radius: ${botSettings.borderRadius === 'square' ? '0' : botSettings.borderRadius === 'pill' ? '20px' : '50%'};
        color: white;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 10px 25px rgba(0,0,0,0.25);
        z-index: 2147483640;
        transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275), box-shadow 0.3s ease;
      }
      #blinkbot-bubble:hover {
        transform: scale(1.1) translateY(-5px);
        box-shadow: 0 15px 30px rgba(0,0,0,0.3);
      }
      #blinkbot-bubble.bottom-right { right: 30px; }
      #blinkbot-bubble.bottom-left { left: 30px; }
      #blinkbot-bubble svg {
        width: 32px;
        height: 32px;
        fill: none;
        stroke: currentColor;
        stroke-width: 2;
        stroke-linecap: round;
        stroke-linejoin: round;
      }
      
      /* Initial Loader CSS */
      .rm-loader-spinner {
        width: 28px;
        height: 28px;
        border: 4px solid rgba(255, 255, 255, 0.3);
        border-top: 4px solid white;
        border-radius: 50%;
        animation: rm-spin 1s linear infinite;
      }
      @keyframes rm-spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }

      #blinkbot-window {
        position: fixed;
        bottom: 105px;
        width: 400px;
        height: 600px;
        min-width: 320px;
        min-height: 450px;
        max-height: calc(100vh - 140px);
        max-width: calc(100vw - 60px);
        background: rgba(255, 255, 255, 0.85);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.5);
        border-radius: ${botSettings.borderRadius === 'square' ? '0' : botSettings.borderRadius === 'pill' ? '24px' : '16px'};
        box-shadow: 0 16px 40px rgba(0,0,0,0.2);
        display: none;
        flex-direction: column;
        overflow: hidden; /* Keeps child elements inside */
        resize: both; /* Makes window resizable */
        z-index: 2147483641;
        font-family: ${botSettings.fontFamily === 'system-ui' ? '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif' : botSettings.fontFamily + ', sans-serif'};
        animation: rm-fade-in 0.3s ease-out;
      }
      @keyframes rm-fade-in {
        from { opacity: 0; transform: translateY(15px); }
        to { opacity: 1; transform: translateY(0); }
      }
      #blinkbot-window.bottom-right { right: 30px; }
      #blinkbot-window.bottom-left { left: 30px; }
      #blinkbot-window.open { display: flex; }
      
      .rm-header {
        color: white;
        padding: 18px 24px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: linear-gradient(135deg, ${botSettings.themeColor}, #333);
        flex-shrink: 0;
      }
      .rm-header h4 { margin: 0; font-size: 1.05rem; font-weight: 600; letter-spacing: 0.5px; }
      .rm-header p { margin: 4px 0 0 0; font-size: 0.8rem; opacity: 0.9; }
      
      .rm-close { background: none; border: none; color: white; font-size: 1.8rem; cursor: pointer; opacity: 0.8; padding: 0; line-height: 1; transition: opacity 0.2s;}
      .rm-close:hover { opacity: 1; }
      
      .rm-messages {
        flex: 1;
        overflow-y: auto;
        padding: 24px;
        display: flex;
        flex-direction: column;
        gap: 16px;
        background: transparent;
      }
      /* Custom Scrollbar for UI polish */
      .rm-messages::-webkit-scrollbar { width: 6px; }
      .rm-messages::-webkit-scrollbar-track { background: transparent; }
      .rm-messages::-webkit-scrollbar-thumb { background-color: rgba(0,0,0,0.15); border-radius: 10px; }
      
      .rm-msg {
        max-width: 85%;
        padding: 12px 16px;
        border-radius: ${botSettings.borderRadius === 'square' ? '0' : '14px'};
        font-size: 0.95rem;
        line-height: 1.5;
        word-wrap: break-word;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
      }
      .rm-msg.user { align-self: flex-end; color: white; border-bottom-right-radius: 4px; }
      .rm-msg.bot { align-self: flex-start; background: #f1f5f9; color: #1e293b; border-bottom-left-radius: 4px; border: 1px solid #e2e8f0; }
      
      .rm-input-wrapper { background: white; padding: 16px; border-top: 1px solid #e2e8f0; flex-shrink: 0; }
      .rm-input-area {
        display: flex; gap: 10px; align-items: center; background: #f8fafc;
        border: 1px solid #e2e8f0; border-radius: 999px; padding: 6px 12px;
        transition: border-color 0.2s;
      }
      .rm-input-area:focus-within { border-color: ${botSettings.themeColor}; box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1); }
      .rm-input { flex: 1; border: none; background: transparent; padding: 8px; font-size: 0.95rem; outline: none; color: #334155; }
      
      .rm-send {
        border: none; color: white; border-radius: 50%; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: transform 0.2s, background-color 0.2s;
      }
      .rm-send:hover { transform: scale(1.05); filter: brightness(1.1); }
      .rm-send svg { width: 18px; height: 18px; fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; margin-left: -2px; }
      
      .rm-brand { text-align: center; font-size: 11px; color: #94a3b8; margin-top: 10px; font-weight: 500;}
      
      .rm-typing { display: flex; gap: 5px; align-items: center; padding: 8px; }
      .rm-dot { width: 6px; height: 6px; background: #94a3b8; border-radius: 50%; animation: rm-bounce 1.4s infinite ease-in-out both; }
      .rm-dot:nth-child(1) { animation-delay: -0.32s; } .rm-dot:nth-child(2) { animation-delay: -0.16s; }
      @keyframes rm-bounce { 0%, 80%, 100% { transform: scale(0); } 40% { transform: scale(1.0); } }
      
      /* Add resize handle styling space (prevents text overlap over native resize handle) */
      #blinkbot-window::after { content: ''; position: absolute; bottom: 0; right: 0; width: 15px; height: 15px; pointer-events: none; }
    `;
    document.head.appendChild(styleEl);
  }

  // 4. Create and inject HTML elements[cite: 1]
  function injectHTML() {
    // Bubble Trigger (Starts with Loader)
    const bubble = document.createElement('div');
    bubble.id = 'blinkbot-bubble';
    bubble.style.backgroundColor = botSettings.themeColor;
    bubble.className = botSettings.position;
    bubble.innerHTML = `<div class="rm-loader-spinner"></div>`;
    bubble.onclick = toggleChat;
    document.body.appendChild(bubble);

    // Chat Window[cite: 1]
    const windowDiv = document.createElement('div');
    windowDiv.id = 'blinkbot-window';
    windowDiv.className = `${botSettings.position}`;
    windowDiv.innerHTML = `
      <div class="rm-header">
        <div style="display: flex; gap: 14px; align-items: center;">
          <div style="width: 38px; height: 38px; border-radius: 50%; background: rgba(255,255,255,0.25); display: flex; align-items: center; justify-content: center; overflow: hidden; box-shadow: 0 2px 6px rgba(0,0,0,0.1);">
            ${getAvatarHTML(botSettings.avatar, "38px")}
          </div>
          <div>
            <h4>${botSettings.name}</h4>
            <p>Online | Ready to assist</p>
          </div>
        </div>
        <div style="display: flex; align-items: center;">
          <button class="rm-close" id="blinkbot-close-btn">&times;</button>
        </div>
      </div>
      <div class="rm-messages" id="blinkbot-messages">
        <div class="rm-msg bot">${formatText(botSettings.welcomeMessage)}</div>
      </div>
      <div class="rm-input-wrapper">
        <div class="rm-input-area">
          <input type="text" class="rm-input" id="blinkbot-input" placeholder="Type your message...">
          <button class="rm-send" id="blinkbot-send-btn" style="background-color: ${botSettings.themeColor}">
            <svg viewBox="0 0 24 24"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
          </button>
        </div>
        <div class="rm-brand">Powered by BlinkBot</div>
      </div>
    `;

    document.body.appendChild(windowDiv);

    // Add event listeners[cite: 1]
    document.getElementById('blinkbot-close-btn').onclick = toggleChat;
    document.getElementById('blinkbot-send-btn').onclick = handleSend;
    document.getElementById('blinkbot-input').onkeypress = function (e) {
      if (e.key === 'Enter') handleSend();
    };
  }

  // Update bubble after init finishes
  function finishLoading() {
    const bubble = document.getElementById('blinkbot-bubble');
    if (bubble) {
        bubble.innerHTML = botSettings.avatar && botSettings.avatar !== "🤖" ? getAvatarHTML(botSettings.avatar, "32px") : `
        <svg viewBox="0 0 24 24"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>`;
    }
    isInitializing = false;
  }

  function toggleChat() {
    if(isInitializing) return; // Prevent opening while loading
    isOpen = !isOpen;
    const windowEl = document.getElementById('blinkbot-window');
    if (isOpen) {
      windowEl.classList.add('open');
      document.getElementById('blinkbot-input').focus();
    } else {
      windowEl.classList.remove('open');
    }
  }

  // Basic formatting helper[cite: 1]
  function formatText(text) {
    if (window.marked && typeof window.marked.parse === 'function') {
      let clean = text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
      return window.marked.parse(clean);
    }
    let clean = text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    clean = clean.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    return clean.split('\n').join('<br>');
  }

  let ws = null;
  let clientId = Math.random().toString(36).substring(7);

  function getWsUrl() {
    let base = apiUrl.replace('http://', 'ws://').replace('https://', 'wss://');
    return `${base}/ws/widget/chat/${clientId}`;
  }

  function ensureWsConnection() {
    return new Promise((resolve, reject) => {
      if (ws && ws.readyState === WebSocket.OPEN) { resolve(); return; }
      ws = new WebSocket(getWsUrl());
      ws.onopen = () => resolve();
      ws.onerror = (err) => reject(err);
    });
  }

  async function handleSend() {
    const inputEl = document.getElementById('blinkbot-input');
    const text = inputEl.value.trim();
    if (!text) return;

    inputEl.value = '';
    const messagesEl = document.getElementById('blinkbot-messages');

    // 1. Append User Message[cite: 1]
    const userMsg = document.createElement('div');
    userMsg.className = 'rm-msg user';
    userMsg.style.backgroundColor = botSettings.themeColor;
    userMsg.textContent = text;
    messagesEl.appendChild(userMsg);
    messagesEl.scrollTop = messagesEl.scrollHeight;

    // 2. Append Typing/Bot container[cite: 1]
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
            if (streamedResponse === '') botMsg.innerHTML = '';
            streamedResponse += data.content;
            botMsg.innerHTML = formatText(streamedResponse);
            messagesEl.scrollTop = messagesEl.scrollHeight;
          } else if (data.type === 'error') {
            botMsg.innerHTML = `<span style="color: #ef4444;">Error: ${data.content}</span>`;
            ws.removeEventListener('message', onMessage);
          } else if (data.type === 'stream_end') {
            chatHistory.push({ role: 'user', content: text });
            chatHistory.push({ role: 'assistant', content: streamedResponse });
            messagesEl.scrollTop = messagesEl.scrollHeight;
            ws.removeEventListener('message', onMessage);
          }
        } catch (e) { console.error("Parse error", e); }
      };

      ws.addEventListener('message', onMessage);
      ws.send(JSON.stringify({
        type: 'chat_request',
        payload: { chatbot_id: chatbotId, message: text, history: chatHistory, language: currentLanguage }
      }));
    } catch (err) {
      botMsg.innerHTML = `<span style="color: #ef4444;">Error: ${err.message}</span>`;
      messagesEl.scrollTop = messagesEl.scrollHeight;
    }
  }

  // Load marked library dynamically[cite: 1]
  function loadMarked() {
    return new Promise((resolve) => {
      if (window.marked) { resolve(); return; }
      const script = document.createElement('script');
      script.src = 'https://cdn.jsdelivr.net/npm/marked/marked.min.js';
      script.onload = () => resolve();
      script.onerror = () => resolve();
      document.head.appendChild(script);
    });
  }

  // Initialization lifecycle[cite: 1]
  async function init() {
    injectStyles();
    injectHTML(); // Inject UI early to show loader
    await fetchConfig();
    await loadMarked();
    finishLoading(); // Remove loader and show avatar
  }

  if (document.readyState === 'complete' || document.readyState === 'interactive') {
    init();
  } else {
    window.addEventListener('DOMContentLoaded', init);
  }
})();
(function () {
  // 1. Find the current script tag to extract configuration attributes
  const scriptTag = document.currentScript || document.querySelector('script[data-chatbot-id]');

  const chatbotId = scriptTag.getAttribute('data-chatbot-id');
  if (!chatbotId) {
    console.error('BlinkBot Widget Error: data-chatbot-id attribute is missing.');
    return;
  }

  // Configurations with local development fallbacks
  const apiUrl = scriptTag.getAttribute('data-api-url');
  
  // Default Chatbot styling settings
  let botSettings = {
    name: 'BlinkBot Assistant',
    themeColor: '#4f46e5', // Matches the purple in your screenshot
    welcomeMessage: 'Hi there! How can I help you today?',
    position: 'bottom-right',
    avatar: 'https://blinkbot.in/icon.png', // Updated default to your logo
    borderRadius: 'rounded',
    fontFamily: 'system-ui'
  };

  let chatHistory = [];
  let isOpen = false;
  let currentLanguage = 'en';
  let isInitializing = true;

  // 2. Fetch Chatbot Config from API
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
          }
        }
      }
    } catch (err) {
      console.warn('BlinkBot Widget: Failed to fetch settings, using defaults.', err);
    }
  }

  // 3. Inject CSS styles dynamically to match the screenshot UI
  function injectStyles() {
    const styleEl = document.createElement('style');
    styleEl.innerHTML = `
      #blinkbot-bubble {
        position: fixed;
        bottom: 30px;
        width: 60px;
        height: 60px;
        border-radius: 50%;
        color: white;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 2147483640;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
      }
      #blinkbot-bubble:hover {
        transform: scale(1.05);
        box-shadow: 0 6px 16px rgba(0,0,0,0.2);
      }
      #blinkbot-bubble.bottom-right { right: 30px; }
      #blinkbot-bubble.bottom-left { left: 30px; }
      
      .rm-loader-spinner {
        width: 24px;
        height: 24px;
        border: 3px solid rgba(255, 255, 255, 0.3);
        border-top: 3px solid white;
        border-radius: 50%;
        animation: rm-spin 1s linear infinite;
      }
      @keyframes rm-spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }

      #blinkbot-window {
        position: fixed;
        bottom: 105px;
        width: 380px;
        height: 600px;
        min-width: 300px;
        min-height: 400px;
        max-height: calc(100vh - 140px);
        max-width: calc(100vw - 60px);
        background: #ffffff; /* Solid white background matching screenshot */
        border-radius: 12px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.15);
        display: none;
        flex-direction: column;
        overflow: hidden;
        resize: both;
        z-index: 2147483641;
        font-family: ${botSettings.fontFamily === 'system-ui' ? '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif' : botSettings.fontFamily + ', sans-serif'};
        animation: rm-fade-in 0.2s ease-out;
      }
      @keyframes rm-fade-in {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
      }
      #blinkbot-window.bottom-right { right: 30px; }
      #blinkbot-window.bottom-left { left: 30px; }
      #blinkbot-window.open { display: flex; }
      
      .rm-header {
        color: white;
        padding: 16px 20px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: linear-gradient(135deg, #5b549e, #3a3668); /* Dark purple gradient matching screenshot */
        flex-shrink: 0;
      }
      .rm-header h4 { margin: 0; font-size: 1.05rem; font-weight: 600; }
      .rm-header p { margin: 2px 0 0 0; font-size: 0.75rem; opacity: 0.9; }
      
      .rm-close { background: none; border: none; color: white; font-size: 1.5rem; cursor: pointer; opacity: 0.8; padding: 0; line-height: 1; }
      .rm-close:hover { opacity: 1; }
      
      .rm-messages {
        flex: 1;
        overflow-y: auto;
        padding: 20px;
        display: flex;
        flex-direction: column;
        gap: 16px;
        background: #ffffff;
      }
      
      .rm-msg {
        max-width: 85%;
        padding: 12px 16px;
        border-radius: 12px;
        font-size: 0.95rem;
        line-height: 1.5;
        word-wrap: break-word;
      }
      .rm-msg.user { align-self: flex-end; color: white; border-bottom-right-radius: 4px; }
      .rm-msg.bot { align-self: flex-start; background: #f3f4f6; color: #1f2937; border-bottom-left-radius: 4px; }
      
      .rm-input-wrapper { background: #ffffff; padding: 16px; flex-shrink: 0; }
      .rm-input-area {
        display: flex; gap: 8px; align-items: center; background: #ffffff;
        border: 1.5px solid ${botSettings.themeColor}; /* Purple border from screenshot */
        border-radius: 9999px; /* Pill shape */
        padding: 6px 6px 6px 16px;
      }
      .rm-input { flex: 1; border: none; background: transparent; padding: 6px 0; font-size: 0.95rem; outline: none; color: #1f2937; }
      
      .rm-send {
        border: none; color: white; border-radius: 50%; width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: transform 0.2s;
      }
      .rm-send:hover { transform: scale(1.05); }
      .rm-send svg { width: 16px; height: 16px; fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; margin-left: -2px;}
      
      .rm-brand { text-align: center; font-size: 10px; color: #9ca3af; margin-top: 8px; }
      
      .rm-typing { display: flex; gap: 4px; align-items: center; padding: 4px; }
      .rm-dot { width: 5px; height: 5px; background: #9ca3af; border-radius: 50%; animation: rm-bounce 1.4s infinite ease-in-out both; }
      .rm-dot:nth-child(1) { animation-delay: -0.32s; } .rm-dot:nth-child(2) { animation-delay: -0.16s; }
      @keyframes rm-bounce { 0%, 80%, 100% { transform: scale(0); } 40% { transform: scale(1.0); } }
    `;
    document.head.appendChild(styleEl);
  }

  // 4. Create and inject HTML elements
  function injectHTML() {
    // Bubble Trigger (Starts with Loader)
    const bubble = document.createElement('div');
    bubble.id = 'blinkbot-bubble';
    bubble.style.backgroundColor = botSettings.themeColor;
    bubble.className = botSettings.position;
    bubble.innerHTML = `<div class="rm-loader-spinner"></div>`;
    bubble.onclick = toggleChat;
    document.body.appendChild(bubble);

    // Chat Window
    const windowDiv = document.createElement('div');
    windowDiv.id = 'blinkbot-window';
    windowDiv.className = `${botSettings.position}`;
    windowDiv.innerHTML = `
      <div class="rm-header">
        <div style="display: flex; gap: 12px; align-items: center;">
          <!-- Strict 1:1 square configuration for the brand logo -->
          <div style="width: 38px; height: 38px; aspect-ratio: 1/1; display: flex; align-items: center; justify-content: center; overflow: hidden; background: transparent;">
            <img src="https://blinkbot.in/icon.png" style="width: 100%; height: 100%; object-fit: contain; aspect-ratio: 1/1;" alt="BlinkBot Logo" />
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

    document.getElementById('blinkbot-close-btn').onclick = toggleChat;
    document.getElementById('blinkbot-send-btn').onclick = handleSend;
    document.getElementById('blinkbot-input').onkeypress = function (e) {
      if (e.key === 'Enter') handleSend();
    };
  }

  function finishLoading() {
    const bubble = document.getElementById('blinkbot-bubble');
    if (bubble) {
      bubble.innerHTML = `<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>`;
    }
    isInitializing = false;
  }

  function toggleChat() {
    if(isInitializing) return; 
    isOpen = !isOpen;
    const windowEl = document.getElementById('blinkbot-window');
    if (isOpen) {
      windowEl.classList.add('open');
      document.getElementById('blinkbot-input').focus();
    } else {
      windowEl.classList.remove('open');
    }
  }

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

    const userMsg = document.createElement('div');
    userMsg.className = 'rm-msg user';
    userMsg.style.backgroundColor = botSettings.themeColor;
    userMsg.textContent = text;
    messagesEl.appendChild(userMsg);
    messagesEl.scrollTop = messagesEl.scrollHeight;

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

  async function init() {
    injectStyles();
    injectHTML(); 
    await fetchConfig();
    await loadMarked();
    finishLoading(); 
  }

  if (document.readyState === 'complete' || document.readyState === 'interactive') {
    init();
  } else {
    window.addEventListener('DOMContentLoaded', init);
  }
})();
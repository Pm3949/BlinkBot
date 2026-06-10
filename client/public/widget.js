(function () {
  // 1. Find the current script tag to extract configuration attributes
  const scriptTag = document.currentScript || document.querySelector('script[data-chatbot-id]');

  const chatbotId = scriptTag.getAttribute('data-chatbot-id');
  if (!chatbotId) {
    console.error('RAGMate Widget Error: data-chatbot-id attribute is missing.');
    return;
  }

  // Configurations with local development fallbacks
  const apiUrl = scriptTag.getAttribute('data-api-url') || 'https://ragmate.onrender.com';
  const supabaseUrl = scriptTag.getAttribute('data-supabase-url') || 'https://phqaaugotzmxjgjzhvhp.supabase.co';
  const supabaseKey = scriptTag.getAttribute('data-supabase-key') || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBocWFhdWdvdHpteGpnanpodmhwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzk4ODUxNjcsImV4cCI6MjA5NTQ2MTE2N30.dUDdQVQgRrDYQWR8IiVw2DNNDlfg8XxD14rLjBAuDE0';

  // Default Chatbot styling settings
  let botSettings = {
    name: 'RAGMate Assistant',
    themeColor: '#4f46e5',
    welcomeMessage: 'Hi there! How can I help you today?',
    position: 'bottom-right',
    avatar: '🤖',
    borderRadius: 'rounded',
    fontFamily: 'system-ui'
  };

  let chatHistory = [];
  let isOpen = false;

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
      console.warn('RAGMate Widget: Failed to fetch settings from Supabase, using defaults.', err);
    }
  }

  // 3. Inject CSS styles dynamically
  function injectStyles() {
    const styleEl = document.createElement('style');
    styleEl.innerHTML = `
      #ragmate-bubble {
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
      #ragmate-bubble:hover {
        transform: scale(1.08);
      }
      #ragmate-bubble.bottom-right {
        right: 30px;
      }
      #ragmate-bubble.bottom-left {
        left: 30px;
      }
      #ragmate-bubble svg {
        width: 28px;
        height: 28px;
        fill: none;
        stroke: currentColor;
        stroke-width: 2;
        stroke-linecap: round;
        stroke-linejoin: round;
      }
      #ragmate-window {
        position: fixed;
        bottom: 105px;
        width: 380px;
        height: 580px;
        max-height: calc(100vh - 140px);
        max-width: calc(100vw - 60px);
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: ${botSettings.borderRadius === 'square' ? '0' : botSettings.borderRadius === 'pill' ? '24px' : '16px'};
        box-shadow: 0 12px 36px rgba(0,0,0,0.15);
        display: none;
        flex-direction: column;
        overflow: hidden;
        z-index: 2147483641;
        font-family: ${botSettings.fontFamily === 'system-ui' ? '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif' : botSettings.fontFamily + ', sans-serif'};
      }
      #ragmate-window.bottom-right {
        right: 30px;
      }
      #ragmate-window.bottom-left {
        left: 30px;
      }
      #ragmate-window.open {
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
      .rm-messages {
        flex: 1;
        overflow-y: auto;
        padding: 20px;
        display: flex;
        flex-direction: column;
        gap: 12px;
        background: #f8fafc;
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
        background: white;
        border-top: 1px solid #e2e8f0;
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
    `;
    document.head.appendChild(styleEl);
  }

  // 4. Create and inject HTML elements
  function injectHTML() {
    // Bubble Trigger
    const bubble = document.createElement('div');
    bubble.id = 'ragmate-bubble';
    bubble.style.backgroundColor = botSettings.themeColor;
    bubble.className = botSettings.position;
    bubble.innerHTML = botSettings.avatar && botSettings.avatar !== "🤖" ? \`<span style="font-size: 24px;">\${botSettings.avatar}</span>\` : \`
      <svg viewBox="0 0 24 24">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
      </svg>
    \`;
    bubble.onclick = toggleChat;
    document.body.appendChild(bubble);

    // Chat Window
    const windowDiv = document.createElement('div');
    windowDiv.id = 'ragmate-window';
    windowDiv.className = `${botSettings.position}`;
    windowDiv.innerHTML = `
      <div class="rm-header" style="background-color: ${botSettings.themeColor}">
        <div style="display: flex; gap: 12px; align-items: center;">
          <div style="width: 32px; height: 32px; border-radius: 50%; background: rgba(255,255,255,0.2); display: flex; align-items: center; justify-content: center; font-size: 16px;">
            ${botSettings.avatar || '🤖'}
          </div>
          <div>
            <h4>${botSettings.name}</h4>
            <p>Online | Powered by RAGMate</p>
          </div>
        </div>
        <button class="rm-close" id="ragmate-close-btn">&times;</button>
      </div>
      <div class="rm-messages" id="ragmate-messages">
        <div class="rm-msg bot">${botSettings.welcomeMessage}</div>
      </div>
      <div style="background: white;">
        <div class="rm-input-area">
          <input type="text" class="rm-input" id="ragmate-input" placeholder="Ask a question...">
          <button class="rm-send" id="ragmate-send-btn" style="background-color: ${botSettings.themeColor}">
            <svg viewBox="0 0 24 24">
              <line x1="22" y1="2" x2="11" y2="13"></line>
              <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
            </svg>
          </button>
        </div>
        <div class="rm-brand">Powered by RAGMate</div>
      </div>
    `;

    document.body.appendChild(windowDiv);

    // Add event listeners
    document.getElementById('ragmate-close-btn').onclick = toggleChat;
    document.getElementById('ragmate-send-btn').onclick = handleSend;
    document.getElementById('ragmate-input').onkeypress = function (e) {
      if (e.key === 'Enter') handleSend();
    };
  }

  function toggleChat() {
    isOpen = !isOpen;
    const windowEl = document.getElementById('ragmate-window');
    if (isOpen) {
      windowEl.classList.add('open');
      document.getElementById('ragmate-input').focus();
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

  async function handleSend() {
    const inputEl = document.getElementById('ragmate-input');
    const text = inputEl.value.trim();
    if (!text) return;

    inputEl.value = '';

    const messagesEl = document.getElementById('ragmate-messages');

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

    // 3. Post chat call
    try {
      const response = await fetch(`${apiUrl}/api/widget/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          chatbot_id: chatbotId,
          message: text,
          history: chatHistory
        })
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: 'Service error' }));
        throw new Error(err.detail || 'Service error');
      }

      // Read chunk stream
      botMsg.innerHTML = '';
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let streamedResponse = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        streamedResponse += chunk;
        botMsg.innerHTML = formatText(streamedResponse);
        messagesEl.scrollTop = messagesEl.scrollHeight;
      }

      // Add to conversation memory
      chatHistory.push({ role: 'user', content: text });
      chatHistory.push({ role: 'assistant', content: streamedResponse });

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

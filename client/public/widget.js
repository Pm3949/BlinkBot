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

  const isUrl = (str) => {
    if (!str) return false;
    if (str.startsWith('http://') || str.startsWith('https://') || str.startsWith('/') || str.startsWith('data:image/')) {
      return true;
    }
    if (str.includes('.') && (str.endsWith('.png') || str.endsWith('.jpg') || str.endsWith('.jpeg') || str.endsWith('.svg') || str.endsWith('.gif') || str.includes('/'))) {
      return true;
    }
    return false;
  };

  const getImageUrl = (str) => {
    if (!str) return "";
    if (str.startsWith('http://') || str.startsWith('https://') || str.startsWith('/') || str.startsWith('data:image/')) {
      return str;
    }
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

  // Reusable icon markup (kept as constants so we don't repeat long SVG strings)
  const BUBBLE_ICON = '<svg viewBox="0 0 24 24"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>';
  const SEND_ICON = '<svg viewBox="0 0 24 24"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>';
  const MIC_ICON = '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><line x1="12" y1="19" x2="12" y2="23"></line><line x1="8" y1="23" x2="16" y2="23"></line></svg>';
  const STOP_ICON = '<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" stroke="none"><rect x="6" y="6" width="12" height="12"></rect></svg>';
  const TTS_PLAY_ICON = '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path></svg>';
  const TTS_STOP_ICON = '<svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor" stroke="none"><rect x="6" y="6" width="12" height="12"></rect></svg>';
  const SPINNER = (size) => `<span class="blinkbot-spinner" style="width:${size}px;height:${size}px;"></span>`;

  // 2. Fetch Chatbot Config from API
  async function fetchConfig() {
    try {
      const response = await fetch(`${apiUrl}/api/chatbots/${chatbotId}`, {
        cache: 'no-store'
      });
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
      console.warn('BlinkBot Widget: Failed to fetch settings from API, using defaults.', err);
    }
  }

  // 3. Show a small loading bubble immediately (before config/marked finish loading)
  //    so there's never a blank gap between page load and the widget appearing.
  function showLoadingBubble() {
    const bootStyle = document.createElement('style');
    bootStyle.innerHTML = `
      @keyframes blinkbot-spin { to { transform: rotate(360deg); } }
      @keyframes blinkbot-pop { from { opacity: 0; transform: scale(0.85); } to { opacity: 1; transform: scale(1); } }
      .blinkbot-spinner {
        display: inline-block;
        width: 18px;
        height: 18px;
        border: 2.5px solid currentColor;
        border-right-color: transparent;
        border-radius: 50%;
        animation: blinkbot-spin 0.65s linear infinite;
        vertical-align: middle;
      }
    `;
    document.head.appendChild(bootStyle);

    const bubble = document.createElement('div');
    bubble.id = 'blinkbot-bubble';
    bubble.setAttribute('aria-label', 'Chat widget loading');
    bubble.style.cssText = `
      position: fixed;
      bottom: 30px;
      right: 30px;
      width: 60px;
      height: 60px;
      border-radius: 50%;
      background: #4f46e5;
      color: #fff;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 8px 24px rgba(0,0,0,0.2);
      z-index: 2147483640;
      animation: blinkbot-pop 0.25s ease;
    `;
    bubble.innerHTML = SPINNER(18);
    document.body.appendChild(bubble);
    return bubble;
  }

  // 4. Inject CSS styles dynamically
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
        border: none;
        padding: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 8px 24px rgba(0,0,0,0.22);
        z-index: 2147483640;
        background: var(--blinkbot-accent, #4f46e5);
        background: linear-gradient(135deg, var(--blinkbot-accent, #4f46e5), color-mix(in srgb, var(--blinkbot-accent, #4f46e5) 72%, black));
        transition: transform 0.2s ease, box-shadow 0.2s ease;
      }
      #blinkbot-bubble:hover { transform: scale(1.08); box-shadow: 0 10px 28px rgba(0,0,0,0.28); }
      #blinkbot-bubble:active { transform: scale(0.94); }
      #blinkbot-bubble.bottom-right { right: 30px; }
      #blinkbot-bubble.bottom-left { left: 30px; }
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
        min-width: 300px;
        min-height: 380px;
        max-height: calc(100vh - 140px);
        max-width: calc(100vw - 60px);
        background: #ffffff !important;
        border: 1px solid rgba(226, 232, 240, 0.8);
        border-radius: ${botSettings.borderRadius === 'square' ? '0' : botSettings.borderRadius === 'pill' ? '24px' : '16px'};
        box-shadow: 0 20px 50px rgba(0,0,0,0.18);
        display: flex;
        flex-direction: column;
        overflow: hidden;
        z-index: 2147483641;
        font-family: ${botSettings.fontFamily === 'system-ui' ? '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif' : botSettings.fontFamily + ', sans-serif'};
        opacity: 0;
        visibility: hidden;
        pointer-events: none;
        transform: translateY(16px) scale(0.96);
        transition: opacity 0.22s cubic-bezier(.4,0,.2,1), transform 0.22s cubic-bezier(.4,0,.2,1), visibility 0.22s;
      }
      #blinkbot-window.bottom-right { right: 30px; transform-origin: bottom right; }
      #blinkbot-window.bottom-left { left: 30px; transform-origin: bottom left; }
      #blinkbot-window.open { opacity: 1; visibility: visible; pointer-events: auto; transform: translateY(0) scale(1); }

      .blinkbot-resize-handle {
        position: absolute;
        top: 4px;
        width: 12px;
        height: 12px;
        z-index: 5;
        opacity: 0;
        pointer-events: none;
        border-radius: 3px;
        color: rgba(255,255,255,0.9);
        transition: opacity 0.15s ease;
      }
      .blinkbot-resize-handle.top-left {
        left: 4px;
        cursor: nwse-resize;
        background-image: repeating-linear-gradient(135deg, currentColor 0, currentColor 1.5px, transparent 1.5px, transparent 4px);
      }
      .blinkbot-resize-handle.top-right {
        right: 4px;
        cursor: nesw-resize;
        background-image: repeating-linear-gradient(45deg, currentColor 0, currentColor 1.5px, transparent 1.5px, transparent 4px);
      }
      #blinkbot-window:hover .blinkbot-resize-handle { opacity: 0.85; pointer-events: auto; }
      .blinkbot-resize-handle.resizing { opacity: 0.85; pointer-events: auto; }

      .rm-header {
        color: white;
        padding: 16px 20px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-shrink: 0;
        background: var(--blinkbot-accent, #4f46e5);
        background: linear-gradient(135deg, var(--blinkbot-accent, #4f46e5), color-mix(in srgb, var(--blinkbot-accent, #4f46e5) 75%, black));
      }
      .rm-header h4 { margin: 0; font-size: 1rem; font-weight: 600; }
      .rm-header p { margin: 2px 0 0 0; font-size: 0.75rem; opacity: 0.85; }
      .rm-avatar-wrap { position: relative; width: 32px; height: 32px; flex-shrink: 0; }
      .rm-avatar-inner {
        width: 100%;
        height: 100%;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.2);
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
        box-shadow: 0 0 0 2px rgba(255,255,255,0.3);
      }
      .rm-online-dot {
        position: absolute;
        bottom: -1px;
        right: -1px;
        width: 9px;
        height: 9px;
        border-radius: 50%;
        background: #22c55e;
        border: 2px solid #3730a3;
        border: 2px solid color-mix(in srgb, var(--blinkbot-accent, #4f46e5) 80%, black);
      }
      .rm-close {
        background: none;
        border: none;
        color: white;
        font-size: 1.4rem;
        cursor: pointer;
        opacity: 0.85;
        padding: 0;
        line-height: 1;
        width: 28px;
        height: 28px;
        flex-shrink: 0;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: background 0.15s ease, opacity 0.15s ease;
      }
      .rm-close:hover { opacity: 1; background: rgba(255, 255, 255, 0.18); }
      .rm-lang-select {
        background: rgba(255, 255, 255, 0.12);
        color: white;
        border: 1px solid rgba(255, 255, 255, 0.25);
        border-radius: 6px;
        padding: 4px 6px;
        font-size: 0.72rem;
        cursor: pointer;
        outline: none;
        margin-right: 10px;
        transition: background 0.15s ease;
      }
      .rm-lang-select:hover { background: rgba(255, 255, 255, 0.2); }
      .rm-lang-select option { background: #1e293b; color: white; }

      .rm-messages {
        flex: 1;
        overflow-y: auto;
        padding: 20px;
        display: flex;
        flex-direction: column;
        gap: 12px;
        background: transparent;
      }
      .rm-messages::-webkit-scrollbar { width: 6px; }
      .rm-messages::-webkit-scrollbar-track { background: transparent; }
      .rm-messages::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.18); border-radius: 3px; }

      .rm-msg {
        max-width: 82%;
        padding: 10px 14px;
        border-radius: ${botSettings.borderRadius === 'square' ? '0' : '14px'};
        font-size: 0.9rem;
        line-height: 1.45;
        word-wrap: break-word;
        animation: blinkbot-pop 0.18s ease;
      }
      .rm-msg.user {
        align-self: flex-end;
        color: white;
        border-bottom-right-radius: 3px;
        background: var(--blinkbot-accent, #4f46e5);
        background: linear-gradient(135deg, var(--blinkbot-accent, #4f46e5), color-mix(in srgb, var(--blinkbot-accent, #4f46e5) 80%, black));
        box-shadow: 0 2px 8px rgba(0,0,0,0.12);
      }
      .rm-msg.bot {
        align-self: flex-start;
        background: #f1f5f9 !important;
        color: #1e293b !important;
        border-bottom-left-radius: 3px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
      }

      .rm-footer { background: transparent; flex-shrink: 0; }
      .rm-input-area {
        padding: 12px 16px;
        background: #f8fafc !important;
        border-top: 1px solid #e2e8f0 !important;
        display: flex;
        gap: 8px;
        align-items: center;
      }
      .rm-input {
        flex: 1;
        min-width: 0;
        border: 1.5px solid rgba(203, 213, 225, 0.8);
        background: #ffffff !important;
        color: #1f2937 !important;
        border-radius: ${botSettings.borderRadius === 'square' ? '0' : botSettings.borderRadius === 'pill' ? '9999px' : '10px'};
        padding: 10px 14px;
        font-size: 0.9rem;
        outline: none;
        transition: border-color 0.15s ease, box-shadow 0.15s ease;
      }
      .rm-input::placeholder {
        color: #94a3b8 !important;
        opacity: 1 !important;
      }
      .rm-input:focus {
        border-color: var(--blinkbot-accent, #4f46e5);
        box-shadow: 0 0 0 3px color-mix(in srgb, var(--blinkbot-accent, #4f46e5) 18%, transparent);
      }
      .rm-send {
        border: none;
        color: white;
        border-radius: 10px;
        width: 38px;
        height: 38px;
        flex-shrink: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        background: var(--blinkbot-accent, #4f46e5);
        background: linear-gradient(135deg, var(--blinkbot-accent, #4f46e5), color-mix(in srgb, var(--blinkbot-accent, #4f46e5) 78%, black));
        transition: filter 0.15s ease, transform 0.15s ease, opacity 0.15s ease;
      }
      .rm-send:hover:not(:disabled) { filter: brightness(1.1); transform: translateY(-1px); }
      .rm-send:active:not(:disabled) { transform: translateY(0) scale(0.95); }
      .rm-send:disabled { opacity: 0.55; cursor: not-allowed; }
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
        display: block;
        text-align: center;
        font-size: 10px;
        color: #94a3b8;
        margin-top: 4px;
        padding-bottom: 8px;
        text-decoration: none;
        transition: color 0.15s ease;
      }
      .rm-brand:hover { color: var(--blinkbot-accent, #64748b); text-decoration: underline; }

      .rm-typing { display: flex; gap: 4px; align-items: center; padding: 4px 8px; }
      .rm-dot {
        width: 5px;
        height: 5px;
        background: #64748b;
        background: color-mix(in srgb, var(--blinkbot-accent, #64748b) 65%, #64748b);
        border-radius: 50%;
        animation: rm-bounce 1.4s infinite ease-in-out both;
      }
      .rm-dot:nth-child(1) { animation-delay: -0.32s; }
      .rm-dot:nth-child(2) { animation-delay: -0.16s; }
      @keyframes rm-bounce { 0%, 80%, 100% { transform: scale(0); } 40% { transform: scale(1.0); } }

      .rm-mic {
        border: none;
        background: transparent;
        color: #64748b;
        width: 38px;
        height: 38px;
        flex-shrink: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        border-radius: 10px;
        transition: color 0.2s, background 0.2s;
      }
      .rm-mic:hover:not(:disabled) { color: #334155; background: rgba(0,0,0,0.05); }
      .rm-mic:disabled { cursor: default; }
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

      /* Markdown Rendering styles */
      .rm-msg.bot ul, .rm-msg.bot ol { margin: 8px 0; padding-left: 20px; }
      .rm-msg.bot ul { list-style-type: disc; }
      .rm-msg.bot ol { list-style-type: decimal; }
      .rm-msg.bot li { margin-bottom: 4px; }
      .rm-msg.bot p { margin: 0 0 8px 0; }
      .rm-msg.bot p:last-child { margin-bottom: 0; }
      .rm-msg.bot h1, .rm-msg.bot h2, .rm-msg.bot h3, .rm-msg.bot h4, .rm-msg.bot h5, .rm-msg.bot h6 {
        margin: 12px 0 6px 0;
        font-weight: 600;
        line-height: 1.25;
      }
      .rm-msg.bot h1 { font-size: 1.3rem; }
      .rm-msg.bot h2 { font-size: 1.2rem; }
      .rm-msg.bot h3 { font-size: 1.1rem; }
      .rm-msg.bot h4 { font-size: 1rem; }
      .rm-msg.bot pre {
        background: rgba(0,0,0,0.06);
        padding: 8px 12px;
        border-radius: 8px;
        overflow-x: auto;
        margin: 8px 0;
      }
      .rm-msg.bot code {
        font-family: monospace;
        font-size: 0.85em;
        background: rgba(0,0,0,0.06);
        padding: 2px 4px;
        border-radius: 4px;
      }
      .rm-msg.bot pre code { background: transparent; padding: 0; border-radius: 0; }
      .rm-msg.bot blockquote {
        border-left: 3px solid var(--blinkbot-accent, #cbd5e1);
        padding-left: 12px;
        margin: 8px 0;
        color: #64748b;
      }
      .rm-msg.bot table { border-collapse: collapse; width: 100%; margin: 8px 0; }
      .rm-msg.bot th, .rm-msg.bot td { border: 1px solid #cbd5e1; padding: 6px 10px; text-align: left; }
      .rm-msg.bot th { background: rgba(0,0,0,0.05); }
    `;
    document.head.appendChild(styleEl);
  }

  // 5. Create and inject HTML elements (upgrades the loading bubble in place)
  function injectHTML(bubble) {
    bubble.removeAttribute('style');
    bubble.className = botSettings.position;
    bubble.style.setProperty('--blinkbot-accent', botSettings.themeColor);
    bubble.setAttribute('aria-label', `Open ${botSettings.name} chat`);
    bubble.title = botSettings.name;
    bubble.innerHTML = BUBBLE_ICON;
    bubble.onclick = toggleChat;
    bubble.style.animation = 'blinkbot-pop 0.35s cubic-bezier(.34,1.56,.64,1)';

    const isRightPos = botSettings.position !== 'bottom-left';

    // Chat Window
    const windowDiv = document.createElement('div');
    windowDiv.id = 'blinkbot-window';
    windowDiv.className = `${botSettings.position}`;
    windowDiv.style.setProperty('--blinkbot-accent', botSettings.themeColor);
    windowDiv.innerHTML = `
      <div class="blinkbot-resize-handle ${isRightPos ? 'top-left' : 'top-right'}" id="blinkbot-resize-handle" title="Drag to resize" aria-hidden="true"></div>
      <div class="rm-header">
        <div style="display: flex; gap: 10px; align-items: center;">
          <a href="https://blinkbot.in" target="_blank" rel="noopener noreferrer" title="BlinkBot" style="display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
            <div style="width: 38px; height: 38px; aspect-ratio: 1/1; display: flex; align-items: center; justify-content: center; overflow: hidden; background: transparent; border-radius: 50%;">
              <img src="https://blinkbot.in/iconq.png" style="width: 100%; height: 100%; object-fit: cover; aspect-ratio: 1/1; border-radius: 50%;" alt="BlinkBot Logo" />
            </div>
          </a>
          <div>
            <h4>${botSettings.name}</h4>
            <p> · Powered by BlinkBot</p>
          </div>
        </div>
        <div style="display: flex; align-items: center;">
          <select id="blinkbot-lang-select" class="rm-lang-select" title="Select STT/TTS Language">
            ${LANGUAGES.map(l => `<option value="${l.id}">${l.name}</option>`).join('')}
          </select>
          <button class="rm-close" id="blinkbot-close-btn" aria-label="Close chat">&times;</button>
        </div>
      </div>
      <div class="rm-messages" id="blinkbot-messages">
        <div class="rm-msg bot">${formatText(botSettings.welcomeMessage)}</div>
      </div>
      <div class="rm-footer">
        <div class="rm-input-area">
          <input type="text" class="rm-input" id="blinkbot-input" placeholder="Ask a question..." aria-label="Message">
          <button class="rm-mic" id="blinkbot-mic-btn" title="Start recording" aria-label="Start voice recording">${MIC_ICON}</button>
          <button class="rm-send" id="blinkbot-send-btn" aria-label="Send message">${SEND_ICON}</button>
        </div>
        <a class="rm-brand" href="https://blinkbot.in" target="_blank" rel="noopener noreferrer">Powered by BlinkBot</a>
      </div>
    `;

    document.body.appendChild(windowDiv);
    setupResize(windowDiv);

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

  // 6. Manual drag-to-resize for the chat window (grows from the free corner,
  //    keeps the anchored bottom/side edges pinned in place).
  function setupResize(windowEl) {
    const handle = windowEl.querySelector('#blinkbot-resize-handle');
    if (!handle) return;
    const isRightPos = windowEl.classList.contains('bottom-right');

    const MIN_W = 300;
    const MIN_H = 380;
    const maxW = () => Math.min(760, window.innerWidth - 40);
    const maxH = () => Math.min(880, window.innerHeight - 40);

    let startX = 0, startY = 0, startW = 0, startH = 0, dragging = false;

    handle.addEventListener('pointerdown', (e) => {
      dragging = true;
      startX = e.clientX;
      startY = e.clientY;
      const rect = windowEl.getBoundingClientRect();
      startW = rect.width;
      startH = rect.height;
      windowEl.style.maxWidth = 'none';
      windowEl.style.maxHeight = 'none';
      handle.classList.add('resizing');
      document.body.style.userSelect = 'none';
      handle.setPointerCapture(e.pointerId);
      e.preventDefault();
    });

    handle.addEventListener('pointermove', (e) => {
      if (!dragging) return;
      const dx = e.clientX - startX;
      const dy = e.clientY - startY;
      let w = isRightPos ? startW - dx : startW + dx;
      let h = startH - dy;
      w = Math.min(Math.max(w, MIN_W), maxW());
      h = Math.min(Math.max(h, MIN_H), maxH());
      windowEl.style.width = w + 'px';
      windowEl.style.height = h + 'px';
    });

    const stopDrag = (e) => {
      if (!dragging) return;
      dragging = false;
      handle.classList.remove('resizing');
      document.body.style.userSelect = '';
      try { handle.releasePointerCapture(e.pointerId); } catch (err) {}
    };
    handle.addEventListener('pointerup', stopDrag);
    handle.addEventListener('pointercancel', stopDrag);

    // Double-click the handle to reset to the default size
    handle.addEventListener('dblclick', () => {
      windowEl.style.width = '';
      windowEl.style.height = '';
      windowEl.style.maxWidth = '';
      windowEl.style.maxHeight = '';
    });

    // Keep a manually-resized window from spilling off-screen if the
    // browser window itself gets resized/rotated afterwards.
    window.addEventListener('resize', () => {
      const rect = windowEl.getBoundingClientRect();
      if (rect.width > maxW()) windowEl.style.width = maxW() + 'px';
      if (rect.height > maxH()) windowEl.style.height = maxH() + 'px';
    });
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
      // Show a loading state while the recording is transcribed
      micBtn.disabled = true;
      micBtn.innerHTML = SPINNER(16);
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
        } finally {
          micBtn.disabled = false;
          micBtn.innerHTML = MIC_ICON;
        }
      };

      mediaRecorder.start();
      isRecording = true;
      micBtn.classList.add('recording');
      micBtn.innerHTML = STOP_ICON;
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

  // Basic formatting helper (bold, code, simple line breaks) falling back if marked is not ready
  function formatText(text) {
    if (window.marked && typeof window.marked.parse === 'function') {
      let clean = text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
      return window.marked.parse(clean);
    }
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
    ttsBtn.innerHTML = TTS_PLAY_ICON;

    ttsBtn.onclick = async () => {
      if (isSpeaking) {
        if (currentAudio) {
          currentAudio.pause();
          currentAudio.src = "";
        }
        isSpeaking = false;
        ttsBtn.innerHTML = TTS_PLAY_ICON;
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
        ttsBtn.innerHTML = SPINNER(14);

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
        ttsBtn.innerHTML = TTS_STOP_ICON;
        currentAudio.onended = () => {
          isSpeaking = false;
          ttsBtn.innerHTML = TTS_PLAY_ICON;
          URL.revokeObjectURL(url);
        };

        currentAudio.play();
      } catch (err) {
        console.error("TTS Error:", err);
        isSpeaking = false;
        ttsBtn.innerHTML = TTS_PLAY_ICON;
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
    const sendBtn = document.getElementById('blinkbot-send-btn');

    // 1. Append User Message
    const userMsg = document.createElement('div');
    userMsg.className = 'rm-msg user';
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

    // Loading state on the send button while a response is in flight
    sendBtn.disabled = true;
    sendBtn.innerHTML = SPINNER(16);
    const restoreSendBtn = () => {
      sendBtn.disabled = false;
      sendBtn.innerHTML = SEND_ICON;
    };

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
            restoreSendBtn();
          } else if (data.type === 'stream_end') {
            chatHistory.push({ role: 'user', content: text });
            chatHistory.push({ role: 'assistant', content: streamedResponse });
            addTTSButton(botMsg, streamedResponse);
            messagesEl.scrollTop = messagesEl.scrollHeight;
            ws.removeEventListener('message', onMessage);
            restoreSendBtn();
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
      restoreSendBtn();
    }
  }

  // Load marked library dynamically
  function loadMarked() {
    return new Promise((resolve) => {
      if (window.marked) {
        resolve();
        return;
      }
      const script = document.createElement('script');
      script.src = 'https://cdn.jsdelivr.net/npm/marked/marked.min.js';
      script.onload = () => resolve();
      script.onerror = () => {
        console.warn('BlinkBot Widget: Failed to load marked library, falling back to basic parsing.');
        resolve();
      };
      document.head.appendChild(script);
    });
  }

  // Initialization lifecycle
  async function init() {
    const bubble = showLoadingBubble();
    try {
      await fetchConfig();
      await loadMarked();
      injectStyles();
      injectHTML(bubble);
    } catch (err) {
      console.error('BlinkBot Widget: Failed to initialize, falling back to defaults.', err);
      try {
        injectStyles();
        injectHTML(bubble);
      } catch (err2) {
        console.error('BlinkBot Widget: Unrecoverable init error.', err2);
      }
    }
  }

  if (document.readyState === 'complete' || document.readyState === 'interactive') {
    init();
  } else {
    window.addEventListener('DOMContentLoaded', init);
  }
})();
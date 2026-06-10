import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Save, Code, Copy, CheckCircle2, Palette, Shield, Key, Globe, Terminal, RefreshCw } from "lucide-react";
import { useChatbotById, useUpdateChatbot } from "../hooks/useChatbots";
import { useUIStore } from "../store/useUIStore";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import LoadingSkeleton from "../components/shared/LoadingSkeleton";
import { toast } from "sonner";

export default function ChatbotEditorPage() {
  const { chatbotId } = useParams();
  const activeWorkspaceId = useUIStore((state) => state.activeWorkspaceId);
  const { data: chatbot, isLoading, isError } = useChatbotById(chatbotId);
  const updateChatbotMutation = useUpdateChatbot(activeWorkspaceId);

  const [name, setName] = useState("");
  const [settings, setSettings] = useState({
    themeColor: "#3B82F6",
    welcomeMessage: "Hi there! How can I help you today?",
    position: "bottom-right",
    avatar: "🤖",
    borderRadius: "rounded",
    fontFamily: "system-ui",
  });
  const [allowedDomains, setAllowedDomains] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [copiedScript, setCopiedScript] = useState(false);
  const [copiedReact, setCopiedReact] = useState(false);
  const [copiedCurl, setCopiedCurl] = useState(false);
  const [copiedKey, setCopiedKey] = useState(false);

  useEffect(() => {
    if (chatbot) {
      setName(chatbot.name);

      let parsedSettings = chatbot.settings;
      if (typeof parsedSettings === 'string') {
        try {
          parsedSettings = JSON.parse(parsedSettings);
        } catch (e) {
          parsedSettings = {};
        }
      }

      setSettings({
        themeColor: parsedSettings?.themeColor || "#3B82F6",
        welcomeMessage: parsedSettings?.welcomeMessage || "Hi there! How can I help you today?",
        position: parsedSettings?.position || "bottom-right",
        avatar: parsedSettings?.avatar || "🤖",
        borderRadius: parsedSettings?.borderRadius || "rounded",
        fontFamily: parsedSettings?.fontFamily || "system-ui",
      });
      setAllowedDomains(chatbot.allowed_domains || "");
      setApiKey(chatbot.api_key || "");
    }
  }, [chatbot]);

  const generateApiKey = () => {
    const newKey = "rm_" + Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
    setApiKey(newKey);
  };

  const handleSave = async () => {
    try {
      await updateChatbotMutation.mutateAsync({
        id: chatbotId,
        payload: {
          name,
          settings,
          allowed_domains: allowedDomains,
          api_key: apiKey
        },
      });
      toast.success("Chatbot settings saved!");
    } catch (error) {
      console.error(error);
      toast.error(error.message || "Failed to save settings");
    }
  };

  // Dynamically use the current frontend's domain for the widget.js script URL
  const embedCode = `<!-- RAGMate Chatbot Widget -->\n
<script defer src="${window.location.origin}/widget.js"
  data-chatbot-id="${chatbotId}">
</script>`;

  const reactCode = `import { useEffect } from 'react';

export default function ChatbotWidget() {
  useEffect(() => {
    const script = document.createElement('script');
    script.src = "${window.location.origin}/widget.js";
    script.defer = true;
    script.setAttribute('data-chatbot-id', "${chatbotId}");
    document.body.appendChild(script);
    
    return () => {
      document.body.removeChild(script);
    };
  }, []);

  return null;
}`;

  const curlCode = `curl -X POST ${window.location.origin}/api/v1/chat \\
  -H "Content-Type: application/json" \\
  -H "x-api-key: ${apiKey || "YOUR_API_KEY"}" \\
  -d '{"message": "Hello!"}'`;

  const copyToClipboard = (text, setter) => {
    navigator.clipboard.writeText(text);
    setter(true);
    setTimeout(() => setter(false), 2000);
    toast.success("Copied to clipboard!");
  };

  if (isLoading) {
    return <div className="p-10"><LoadingSkeleton /></div>;
  }

  if (isError || !chatbot) {
    return <div className="p-10 text-red-500">Failed to load chatbot details.</div>;
  }

  return (
    <div className="h-full flex flex-col p-6 max-w-[1200px] mx-auto w-full space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link to="/chatbots" className="p-2 hover:bg-muted rounded-xl transition">
            <ArrowLeft size={20} />
          </Link>
          <div>
            <h1 className="text-3xl font-bold text-foreground">Widget Editor</h1>
            <p className="text-muted-foreground mt-1">Configure {chatbot.name}</p>
          </div>
        </div>
        <button
          onClick={handleSave}
          disabled={updateChatbotMutation.isPending}
          className="flex items-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-sm font-medium text-white transition hover:bg-primary/90 disabled:opacity-70"
        >
          <Save size={16} />
          {updateChatbotMutation.isPending ? "Saving..." : "Save Changes"}
        </button>
      </div>

      <div className="grid lg:grid-cols-2 gap-8 mt-6">
        {/* Customization Panel */}
        <div className="space-y-6">
          <div className="glass-card p-6">
            <div className="flex items-center gap-2 mb-6 text-lg font-semibold">
              <Palette size={20} className="text-primary" />
              Appearance
            </div>

            <div className="space-y-5">
              <div className="space-y-2">
                <label className="text-sm font-medium">Chatbot Name (Public)</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full rounded-xl border border-border bg-background px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Welcome Message</label>
                <input
                  type="text"
                  value={settings.welcomeMessage || ""}
                  onChange={(e) => setSettings({ ...settings, welcomeMessage: e.target.value })}
                  className="w-full rounded-xl border border-border bg-background px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Theme Color</label>
                <div className="flex items-center gap-4">
                  <input
                    type="color"
                    value={settings.themeColor || "#3B82F6"}
                    onChange={(e) => setSettings({ ...settings, themeColor: e.target.value })}
                    className="h-10 w-14 rounded-lg cursor-pointer bg-transparent border-0 p-0"
                  />
                  <input
                    type="text"
                    value={settings.themeColor || "#3B82F6"}
                    onChange={(e) => setSettings({ ...settings, themeColor: e.target.value })}
                    className="flex-1 rounded-xl border border-border bg-background px-4 py-2 text-sm uppercase focus:outline-none focus:ring-2 focus:ring-primary/50"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Widget Position</label>
                <Select
                  value={settings.position || "bottom-right"}
                  onValueChange={(value) => setSettings({ ...settings, position: value })}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select position" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="bottom-right">Bottom Right</SelectItem>
                    <SelectItem value="bottom-left">Bottom Left</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Avatar Emoji</label>
                  <input
                    type="text"
                    maxLength="2"
                    value={settings.avatar || "🤖"}
                    onChange={(e) => setSettings({ ...settings, avatar: e.target.value })}
                    className="w-full rounded-xl border border-border bg-background px-4 py-2.5 text-center text-xl focus:outline-none focus:ring-2 focus:ring-primary/50"
                  />
                </div>
                
                <div className="space-y-2">
                  <label className="text-sm font-medium">Border Radius</label>
                  <Select
                    value={settings.borderRadius || "rounded"}
                    onValueChange={(value) => setSettings({ ...settings, borderRadius: value })}
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Select style" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="square">Square</SelectItem>
                      <SelectItem value="rounded">Rounded</SelectItem>
                      <SelectItem value="pill">Pill</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Font Family</label>
                <Select
                  value={settings.fontFamily || "system-ui"}
                  onValueChange={(value) => setSettings({ ...settings, fontFamily: value })}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select font" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="system-ui">System Default</SelectItem>
                    <SelectItem value="Inter">Inter</SelectItem>
                    <SelectItem value="Roboto">Roboto</SelectItem>
                    <SelectItem value="Outfit">Outfit</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>

          <div className="glass-card p-6 border-indigo-500/20 bg-indigo-500/5">
            <div className="flex items-center gap-2 mb-6 text-lg font-semibold text-indigo-600 dark:text-indigo-400">
              <Shield size={20} />
              Security & Integration
            </div>

            <div className="space-y-6">
              {/* Allowed Domains */}
              <div className="space-y-2">
                <label className="text-sm font-medium flex items-center gap-2">
                  <Globe size={16} className="text-muted-foreground" />
                  Allowed Domains
                </label>
                <input
                  type="text"
                  value={allowedDomains}
                  onChange={(e) => setAllowedDomains(e.target.value)}
                  placeholder="e.g. example.com, myapp.dev (comma separated)"
                  className="w-full rounded-xl border border-border bg-background px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                />
                <p className="text-xs text-muted-foreground">
                  Restrict the widget to only load on these domains. Leave empty to allow any domain.
                </p>
              </div>

              {/* API Key */}
              <div className="space-y-2">
                <label className="text-sm font-medium flex items-center gap-2">
                  <Key size={16} className="text-muted-foreground" />
                  Developer API Key
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={apiKey}
                    readOnly
                    placeholder="No API key generated yet"
                    className="w-full rounded-xl border border-border bg-background px-4 py-2.5 text-sm focus:outline-none font-mono text-muted-foreground"
                  />
                  <button
                    onClick={generateApiKey}
                    title="Generate new API Key"
                    className="p-2.5 rounded-xl bg-primary/10 text-primary hover:bg-primary/20 transition"
                  >
                    <RefreshCw size={18} />
                  </button>
                  <button
                    onClick={() => copyToClipboard(apiKey, setCopiedKey)}
                    title="Copy API Key"
                    className="p-2.5 rounded-xl bg-muted text-muted-foreground hover:text-foreground transition"
                  >
                    {copiedKey ? <CheckCircle2 size={18} /> : <Copy size={18} />}
                  </button>
                </div>
                <p className="text-xs text-muted-foreground">
                  Use this key for programmatic server-side access to your chatbot.
                </p>
              </div>

              {/* Code Snippets */}
              <div className="space-y-4 pt-4 border-t border-border">
                <label className="text-sm font-medium flex items-center gap-2">
                  <Code size={16} className="text-muted-foreground" />
                  Integration Snippets
                </label>

                {/* HTML Script */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-muted-foreground uppercase">HTML Script Tag</span>
                    <button onClick={() => copyToClipboard(embedCode, setCopiedScript)} className="text-xs flex items-center gap-1 text-indigo-600 hover:text-indigo-800 transition">
                      {copiedScript ? <CheckCircle2 size={12} /> : <Copy size={12} />} {copiedScript ? "Copied" : "Copy"}
                    </button>
                  </div>
                  <div className="bg-slate-950 rounded-xl p-3 overflow-x-auto">
                    <code className="text-xs text-indigo-300 whitespace-pre">{embedCode}</code>
                  </div>
                </div>

                {/* React */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-muted-foreground uppercase">React Component</span>
                    <button onClick={() => copyToClipboard(reactCode, setCopiedReact)} className="text-xs flex items-center gap-1 text-indigo-600 hover:text-indigo-800 transition">
                      {copiedReact ? <CheckCircle2 size={12} /> : <Copy size={12} />} {copiedReact ? "Copied" : "Copy"}
                    </button>
                  </div>
                  <div className="bg-slate-950 rounded-xl p-3 overflow-x-auto">
                    <code className="text-xs text-indigo-300 whitespace-pre">{reactCode}</code>
                  </div>
                </div>

                {/* cURL */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-muted-foreground uppercase">REST API (cURL)</span>
                    <button onClick={() => copyToClipboard(curlCode, setCopiedCurl)} className="text-xs flex items-center gap-1 text-indigo-600 hover:text-indigo-800 transition">
                      {copiedCurl ? <CheckCircle2 size={12} /> : <Copy size={12} />} {copiedCurl ? "Copied" : "Copy"}
                    </button>
                  </div>
                  <div className="bg-slate-950 rounded-xl p-3 overflow-x-auto">
                    <code className="text-xs text-indigo-300 whitespace-pre">{curlCode}</code>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Live Preview Panel */}
        <div className="glass-card flex flex-col h-[600px] overflow-hidden sticky top-6">
          <div className="border-b border-border p-4 bg-muted/30">
            <h3 className="font-semibold flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-green-500"></span>
              Live Preview
            </h3>
            <p className="text-xs text-muted-foreground mt-1">This is how the widget will appear on your site.</p>
          </div>

          <div className="flex-1 bg-white relative p-4">
            {/* Fake Website Content */}
            <div className="opacity-20 pointer-events-none space-y-4">
              <div className="h-8 w-3/4 bg-gray-300 rounded-md"></div>
              <div className="h-4 w-full bg-gray-200 rounded-md"></div>
              <div className="h-4 w-5/6 bg-gray-200 rounded-md"></div>
              <div className="h-4 w-4/6 bg-gray-200 rounded-md"></div>
            </div>

            {/* Fake Widget UI */}
            <div
              className={`absolute bottom-6 flex flex-col transition-all ${settings.position === 'bottom-left' ? 'left-6 items-start' : 'right-6 items-end'
                }`}
              style={{ fontFamily: settings.fontFamily || 'system-ui' }}
            >
              {/* Chat Window */}
              <div className={`w-[340px] bg-white border border-gray-200 shadow-2xl mb-4 overflow-hidden flex flex-col h-[400px] ${
                settings.borderRadius === 'square' ? 'rounded-none' : 
                settings.borderRadius === 'pill' ? 'rounded-[24px]' : 'rounded-2xl'
              }`}>
                {/* Header */}
                <div
                  className="p-4 text-white font-semibold flex items-center justify-between"
                  style={{ backgroundColor: settings.themeColor || '#3B82F6' }}
                >
                  <div className="flex items-center gap-3">
                    <div className="h-8 w-8 rounded-full bg-white/20 flex items-center justify-center text-sm">
                      {settings.avatar || "🤖"}
                    </div>
                    <span>{name || "Chatbot"}</span>
                  </div>
                  <span className="opacity-70 cursor-pointer">✕</span>
                </div>

                {/* Messages */}
                <div className="flex-1 p-4 bg-gray-50 flex flex-col gap-3">
                  <div className={`bg-white border border-gray-100 p-3 shadow-sm text-sm text-gray-800 self-start max-w-[85%] ${
                    settings.borderRadius === 'square' ? 'rounded-none' : 'rounded-2xl rounded-tl-sm'
                  }`}>
                    {settings.welcomeMessage || "Hi there! How can I help you today?"}
                  </div>
                </div>

                {/* Input */}
                <div className="p-3 border-t border-gray-100 bg-white">
                  <div className="relative">
                    <input
                      type="text"
                      placeholder="Type your message..."
                      className={`w-full bg-gray-50 border border-gray-200 px-4 py-2.5 text-sm focus:outline-none ${
                        settings.borderRadius === 'square' ? 'rounded-none' : 
                        settings.borderRadius === 'pill' ? 'rounded-full' : 'rounded-xl'
                      }`}
                      disabled
                    />
                    <div
                      className={`absolute right-1.5 top-1.5 h-7 w-7 flex items-center justify-center text-white ${
                        settings.borderRadius === 'square' ? 'rounded-none' : 
                        settings.borderRadius === 'pill' ? 'rounded-full' : 'rounded-lg'
                      }`}
                      style={{ backgroundColor: settings.themeColor || '#3B82F6' }}
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
                    </div>
                  </div>
                  <div className="text-center mt-2">
                    <span className="text-[10px] text-gray-400 font-medium">Powered by RAGMate</span>
                  </div>
                </div>
              </div>

              {/* Launcher Button */}
              <div
                className={`h-14 w-14 shadow-lg flex items-center justify-center text-white cursor-pointer hover:scale-105 transition-transform text-2xl ${
                  settings.borderRadius === 'square' ? 'rounded-none' : 
                  settings.borderRadius === 'pill' ? 'rounded-[20px]' : 'rounded-full'
                }`}
                style={{ backgroundColor: settings.themeColor || '#3B82F6' }}
              >
                {settings.avatar && settings.avatar !== "🤖" ? settings.avatar : (
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
                )}
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}

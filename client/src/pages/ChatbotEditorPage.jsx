import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Save, Code, Copy, CheckCircle2, Palette, ChevronDown } from "lucide-react";
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
  });
  const [copied, setCopied] = useState(false);

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
      });
    }
  }, [chatbot]);

  const handleSave = async () => {
    try {
      await updateChatbotMutation.mutateAsync({
        id: chatbotId,
        payload: {
          name,
          settings,
        },
      });
      toast.success("Chatbot settings saved!");
    } catch (error) {
      console.error(error);
      toast.error(error.message || "Failed to save settings");
    }
  };

  // Dynamically use the current frontend's domain for the widget.js script URL
  const embedCode = `<script src="${window.location.origin}/widget.js" data-chatbot-id="${chatbotId}"></script>`;

  const copyEmbedCode = () => {
    navigator.clipboard.writeText(embedCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    toast.success("Embed code copied to clipboard!");
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
            </div>
          </div>

          <div className="glass-card p-6 border-blue-500/20 bg-blue-500/5">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2 text-lg font-semibold text-blue-600 dark:text-blue-400">
                <Code size={20} />
                Embed Code
              </div>
              <button
                onClick={copyEmbedCode}
                className="flex items-center gap-1.5 rounded-lg bg-blue-500/10 px-3 py-1.5 text-sm font-medium text-blue-600 hover:bg-blue-500/20 transition dark:text-blue-400"
              >
                {copied ? <CheckCircle2 size={14} /> : <Copy size={14} />}
                {copied ? "Copied" : "Copy"}
              </button>
            </div>
            <p className="text-sm text-muted-foreground mb-4">
              Copy this script tag and paste it just before the closing <code>&lt;/body&gt;</code> tag of your website.
            </p>
            <div className="bg-slate-900 rounded-xl p-4 overflow-x-auto">
              <code className="text-sm text-blue-300 whitespace-pre">
                {embedCode}
              </code>
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
              className={`absolute bottom-6 flex flex-col transition-all ${
                settings.position === 'bottom-left' ? 'left-6 items-start' : 'right-6 items-end'
              }`}
            >
              {/* Chat Window */}
              <div className="w-[340px] bg-white border border-gray-200 rounded-2xl shadow-2xl mb-4 overflow-hidden flex flex-col h-[400px]">
                {/* Header */}
                <div 
                  className="p-4 text-white font-semibold flex items-center justify-between"
                  style={{ backgroundColor: settings.themeColor || '#3B82F6' }}
                >
                  <div className="flex items-center gap-3">
                    <div className="h-8 w-8 rounded-full bg-white/20 flex items-center justify-center text-sm">
                      🤖
                    </div>
                    <span>{name || "Chatbot"}</span>
                  </div>
                  <span className="opacity-70 cursor-pointer">✕</span>
                </div>
                
                {/* Messages */}
                <div className="flex-1 p-4 bg-gray-50 flex flex-col gap-3">
                  <div className="bg-white border border-gray-100 rounded-2xl rounded-tl-sm p-3 shadow-sm text-sm text-gray-800 self-start max-w-[85%]">
                    {settings.welcomeMessage || "Hi there! How can I help you today?"}
                  </div>
                </div>

                {/* Input */}
                <div className="p-3 border-t border-gray-100 bg-white">
                  <div className="relative">
                    <input 
                      type="text" 
                      placeholder="Type your message..." 
                      className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none"
                      disabled
                    />
                    <div 
                      className="absolute right-1.5 top-1.5 h-7 w-7 rounded-lg flex items-center justify-center text-white"
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
                className="h-14 w-14 rounded-full shadow-lg flex items-center justify-center text-white cursor-pointer hover:scale-105 transition-transform"
                style={{ backgroundColor: settings.themeColor || '#3B82F6' }}
              >
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}

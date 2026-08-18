import { useState, useEffect, useRef } from 'react';
import {
  Bot, Zap, Database, Globe, ArrowRight, Cpu, Sun, Moon,
  Sparkles, Users, Upload, Settings, Code, Brain,
  ChevronRight, ChevronLeft, Check, Send, Loader2, Star,
  CheckCircle2, Play, FileText, ChevronDown, Copy, Eye, Terminal,
  Lightbulb, MessagesSquare, Sliders, HelpCircle, Wrench, Layers,
  ShieldCheck, Clock, TrendingUp, Rocket, BookOpen, MessageSquare,
  AlertCircle, ArrowUpRight, BarChart3, Lock, Puzzle, Search
} from 'lucide-react';
import { toast } from 'sonner';
import { usePageSeo } from './hooks/usePageSeo';

const API_URL = 'https://api.blinkbot.in';

function formatMarkdown(text) {
  if (!text) return "";
  let clean = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
  
  // Headers
  clean = clean.replace(/^#### (.*?)\r?$/gm, '<h4 class="font-bold text-[11px] uppercase tracking-wider text-muted-foreground mt-3 mb-1">$1</h4>');
  clean = clean.replace(/^### (.*?)\r?$/gm, '<h3 class="font-bold text-sm mt-3 mb-1">$1</h3>');
  clean = clean.replace(/^## (.*?)\r?$/gm, '<h2 class="font-bold text-base mt-4 mb-1.5">$1</h2>');
  clean = clean.replace(/^# (.*?)\r?$/gm, '<h1 class="font-extrabold text-lg mt-5 mb-2">$1</h1>');
  
  // Bold
  clean = clean.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  
  // Inline Code
  clean = clean.replace(/`(.*?)`/g, '<code class="bg-muted px-1.5 py-0.5 rounded text-[11px] font-mono">$1</code>');
  
  // Bullets
  clean = clean.replace(/^\* (.*?)\r?$/gm, '• $1');
  clean = clean.replace(/^- (.*?)\r?$/gm, '• $1');
  
  // Line Breaks
  return clean.split('\n').join('<br />');
}

// ─── LLM Provider Data ──────────────────────────────────────────────────────
const LLM_PROVIDERS = [
  { name: "OpenRouter", badge: "Access to Everything", desc: "DeepSeek, Llama 3.3, Qwen & more." },
  { name: "OpenAI", badge: "GPT-4o & More", desc: "The industry benchmark for conversational AI." },
  { name: "Groq", badge: "Lightning Fast", desc: "Near-instant responses via hardware acceleration." },
  { name: "HuggingFace", badge: "Open Source", desc: "Plug in any open-source embedding model." },
  { name: "Anthropic", badge: "Claude Sonnet", desc: "Deep reasoning and careful long-form analysis." },
  { name: "Google Gemini", badge: "Gemini Flash", desc: "Handles massive documents effortlessly." },
];

// ─── Demo Personas for Sandbox ───────────────────────────────────────────────
const DEMO_PERSONAS = [
  {
    id: 'support',
    name: 'Helpdesk Assistant',
    badge: 'Customer Support',
    docsCount: 'Trained on 12 Help Guides',
    avatarBg: 'bg-blue-500',
    icon: MessagesSquare,
    questions: [
      "What is your refund policy?",
      "How do I add my team members?",
      "Can I change the widget color?",
    ],
    responses: {
      "What is your refund policy?": {
        answer: "We offer a full 30-day money-back guarantee, no questions asked. You can cancel or switch your plan anytime from the Billing page in your workspace.",
        sources: ["Refund_Policy.pdf", "Terms_of_Service.md"],
      },
      "How do I add my team members?": {
        answer: "Head to Workspace Settings → Team & Permissions. Click 'Invite Members', enter their email, and choose their role: Admin, Member, or Viewer. They'll get an invitation link instantly.",
        sources: ["Team_Guide.pdf"],
      },
      "Can I change the widget color?": {
        answer: "Absolutely! Open the Widget Configurator in your dashboard, pick any accent color (or enter a hex code), and your live preview updates in real time. Then copy the script tag.",
        sources: ["Widget_Customization.md"],
      },
    },
  },
  {
    id: 'sales',
    name: 'Sales Assistant',
    badge: 'Product Info',
    docsCount: 'Trained on Product Catalogs',
    avatarBg: 'bg-purple-500',
    icon: TrendingUp,
    questions: [
      "What pricing plans do you have?",
      "Do you support open-source models?",
      "Can I buy more messages later?",
    ],
    responses: {
      "What pricing plans do you have?": {
        answer: "We have three tiers: a forever-free Starter plan, Pro at ₹999/mo, and Business at ₹3,999/mo. Annual billing saves you 20% on paid plans. All plans include a free trial period!",
        sources: ["Pricing_2026.pdf"],
      },
      "Do you support open-source models?": {
        answer: "Yes! Connect your OpenRouter or HuggingFace API key to access hundreds of open-source models like DeepSeek R1, Llama 3.3, Mistral, and Qwen, at near-zero cost.",
        sources: ["Supported_Models.pdf"],
      },
      "Can I buy more messages later?": {
        answer: "Of course. Head to Billing and grab a top-up pack: +5,000 messages for ₹299 or +20,000 for ₹899. These credits never expire and stack on top of your plan quota.",
        sources: ["Billing_Guide.pdf"],
      },
    },
  },
  {
    id: 'hr',
    name: 'HR Onboarding Bot',
    badge: 'HR & Policies',
    docsCount: 'Trained on Employee Handbook',
    avatarBg: 'bg-emerald-500',
    icon: Users,
    questions: [
      "Is our company data kept private?",
      "How do I request time off?",
      "What are the office hours?",
    ],
    responses: {
      "Is our company data kept private?": {
        answer: "Yes, completely. Files are isolated per workspace with Row-Level Security enforced at the database level. We never use your data to train public AI models, and everything is encrypted at rest.",
        sources: ["Privacy_Policy.pdf"],
      },
      "How do I request time off?": {
        answer: "Submit a time-off request through the HR portal at least two weeks in advance for planned vacations. For sick days, notify your manager by 9 AM on the day of absence.",
        sources: ["Employee_Handbook.pdf"],
      },
      "What are the office hours?": {
        answer: "Core office hours are 9 AM to 5 PM, Monday through Friday. Most teams have flexible hours: coordinate with your manager. Remote-first teams should overlap at least 3 hours with the core window.",
        sources: ["Office_Policies.pdf"],
      },
    },
  },
];

// ─── FAQ Data ─────────────────────────────────────────────────────────────────
const FAQS = [
  {
    q: "Which AI models can I use?",
    a: "You can connect OpenRouter, OpenAI, Groq, Anthropic Claude, Google Gemini, and HuggingFace. Switch models any time without losing your data or settings. BlinkBot is completely model-agnostic.",
  },
  {
    q: "Do I need to be a developer to use BlinkBot?",
    a: "Not at all. Uploading documents, configuring your bot's personality, and embedding it on your website are all done through a visual no-code interface. The only 'code' you'll ever paste is a single script tag.",
  },
  {
    q: "Is my document data kept private?",
    a: "Absolutely. Your uploaded files are strictly isolated within your workspace, protected by PostgreSQL Row-Level Security. We never share or use your private data to train any public AI models.",
  },
  {
    q: "How do I add the chat widget to my website?",
    a: "Copy the one-line script snippet from the Widget Configurator and paste it into your website's HTML. It works instantly on WordPress, Shopify, Webflow, React, or any other platform.",
  },
  {
    q: "What happens when I run out of messages?",
    a: "Purchase a non-expiring top-up pack from the Billing page at any time. Extra credits stack on top of your monthly allowance and roll over. They never reset.",
  },
  {
    q: "Can I invite my team to collaborate?",
    a: "Yes. Invite colleagues to your workspace and assign granular roles like Admin, Member, or Viewer. Admins can manage agents and data; Viewers can only read. Fine-grained permission toggles let you control exactly what each member can access.",
  },
];

// ─── How It Works Steps ───────────────────────────────────────────────────────
const HOW_IT_WORKS = [
  {
    step: "01",
    icon: Sparkles,
    title: "Prompt to Create Team",
    desc: "Describe your workflow in a single plain-English prompt. BlinkBot instantly generates and configures a whole team of specialized agents with tools assigned.",
    accent: "from-blue-500/20 to-blue-500/5",
    iconColor: "text-blue-500",
    iconBg: "bg-blue-500/10",
  },
  {
    step: "02",
    icon: Upload,
    title: "Connect Knowledge & Tools",
    desc: "Upload PDFs, URLs, or Google Drive files to give them knowledge, and plug in external tools like WhatsApp, SMS, or custom API webhooks.",
    accent: "from-purple-500/20 to-purple-500/5",
    iconColor: "text-purple-500",
    iconBg: "bg-purple-500/10",
  },
  {
    step: "03",
    icon: ShieldCheck,
    title: "Deploy with Approvals",
    desc: "Embed your widgets or launch channels with Human-in-the-Loop settings. Agents will pause and request permission before taking sensitive actions.",
    accent: "from-orange-500/20 to-orange-500/5",
    iconColor: "text-primary",
    iconBg: "bg-primary/10",
  },
];

// ─── Core Feature Cards ───────────────────────────────────────────────────────
const FEATURE_CARDS = [
  {
    icon: Sparkles,
    title: "Zero-Code Agent Creation",
    badge: "1-Prompt Deploy",
    desc: "Describe what you need in plain English. BlinkBot builds, routes, and deploys a custom team of agents with correct tools assigned automatically.",
    gradient: "from-violet-500/10 to-violet-500/0",
    borderHover: "hover:border-violet-500/40",
    iconBg: "bg-violet-500/10",
    iconColor: "text-violet-500",
  },
  {
    icon: Database,
    title: "Chat with Your Data",
    badge: "RAG Engine",
    desc: "Upload manuals, policies, or website links. The AI reads and understands them instantly to answer questions grounded in your content, not hallucinations.",
    gradient: "from-blue-500/10 to-blue-500/0",
    borderHover: "hover:border-blue-500/40",
    iconBg: "bg-blue-500/10",
    iconColor: "text-blue-500",
  },
  {
    icon: Wrench,
    title: "Seamless Tool Integration",
    badge: "Connected APIs",
    desc: "Connect your agents to any external software, databases, CRM systems, or messaging networks. Automate actions across all your favorite platforms natively.",
    gradient: "from-cyan-500/10 to-cyan-500/0",
    borderHover: "hover:border-cyan-500/40",
    iconBg: "bg-cyan-500/10",
    iconColor: "text-cyan-500",
  },
  {
    icon: ShieldCheck,
    title: "Human-in-the-Loop",
    badge: "Safe Automation",
    desc: "Configure sensitive tools (like processing refunds or databases) to pause and require manual admin approval before execution.",
    gradient: "from-primary/10 to-primary/0",
    borderHover: "hover:border-primary/40",
    iconBg: "bg-primary/10",
    iconColor: "text-primary",
  },
  {
    icon: Users,
    title: "Team Workspaces & RBAC",
    badge: "Collaboration",
    desc: "Invite colleagues, assign roles (Admin/Member/Viewer), keep datasets private per workspace, and manage permissions with fine-grained toggles.",
    gradient: "from-emerald-500/10 to-emerald-500/0",
    borderHover: "hover:border-emerald-500/40",
    iconBg: "bg-emerald-500/10",
    iconColor: "text-emerald-500",
  },
  {
    icon: Cpu,
    title: "Bring Your Own AI",
    badge: "Model Choice",
    desc: "Prefer OpenAI, Claude, or open-source models? Plug in your API keys and switch between providers with a single click, with no vendor lock-in.",
    gradient: "from-amber-500/10 to-amber-500/0",
    borderHover: "hover:border-amber-500/40",
    iconBg: "bg-amber-500/10",
    iconColor: "text-amber-500",
  },
  {
    icon: Lock,
    title: "Enterprise-Grade Security",
    badge: "RLS + Encryption",
    desc: "PostgreSQL Row-Level Security enforces tenant isolation at the database kernel. Your API keys are encrypted at rest. Rate limiting protects every endpoint.",
    gradient: "from-rose-500/10 to-rose-500/0",
    borderHover: "hover:border-rose-500/40",
    iconBg: "bg-rose-500/10",
    iconColor: "text-rose-500",
  },
  {
    icon: Wrench,
    title: "Self-Correcting AI",
    badge: "Fix & Learn",
    desc: "Flag wrong answers directly in the chat interface and add your correction. The bot incorporates your feedback instantly, with no model retraining needed.",
    gradient: "from-teal-500/10 to-teal-500/0",
    borderHover: "hover:border-teal-500/40",
    iconBg: "bg-teal-500/10",
    iconColor: "text-teal-500",
  },
];

// ─── Pain Points (Why BlinkBot) ───────────────────────────────────────────────
const PAIN_POINTS = [
  {
    pain: "Repetitive support requests and notifications are overwhelming your operations and team.",
    solve: "BlinkBot automatically routes queries, handles SMS/WhatsApp alerts, and resolves them 24/7.",
    icon: AlertCircle,
  },
  {
    pain: "You want to automate workflows but fear AI will make costly mistakes or perform unauthorized actions.",
    solve: "BlinkBot pauses execution and requests manual human approval for sensitive integrations.",
    icon: AlertCircle,
  },
  {
    pain: "Setting up custom integrations and agent routing requires senior developers and complex codebases.",
    solve: "BlinkBot creates and deploys tool-equipped agent teams via a single plain-English prompt.",
    icon: AlertCircle,
  },
];

// ─── Stats ────────────────────────────────────────────────────────────────────
const STATS = [
  { value: "6+", label: "LLM Providers Supported", icon: Cpu },
  { value: "<60s", label: "Average Onboarding Time", icon: Clock },
  { value: "100%", label: "Private & Isolated Data", icon: ShieldCheck },
  { value: "1-Line", label: "Website Embed Code", icon: Code },
];

function Logo() {
  return (
    <div className="flex items-center gap-3">
      <img 
        src="/logo1.png" 
        alt="BlinkBot Logo" 
        className="h-13 w-auto object-contain rounded-xl" 
      />
      <div>
        <div className="font-bold text-foreground text-left leading-none">
          BlinkBot
        </div>
        <div className="text-xs text-slate-500 text-left mt-1">
          No-Code Chatbots
        </div>
      </div>
    </div>
  );
}

export default function LandingPage() {
  usePageSeo();
  const [darkMode, setDarkMode] = useState(true);

  useEffect(() => {
    // Sync dark mode class on html tag
    document.documentElement.classList.toggle('dark', darkMode);
  }, [darkMode]);

  const toggleDarkMode = () => setDarkMode(!darkMode);

  // Billing cycle
  const [annualBilling, setAnnualBilling] = useState(false);

  // Demo form state
  const [demoForm, setDemoForm] = useState({ name: '', email: '', company: '', message: '' });
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Interactive Sandbox state
  const [activePersona, setActivePersona] = useState(DEMO_PERSONAS[0]);
  const [simChatHistory, setSimChatHistory] = useState([]);
  const [isSimTyping, setIsSimTyping] = useState(false);

  // Widget customizer state
  const [customWidgetColor, setCustomWidgetColor] = useState('#FF4D00');
  const [customWidgetTitle, setCustomWidgetTitle] = useState('BlinkBot Assistant');
  const [customWidgetPosition, setCustomWidgetPosition] = useState('right');
  const [copiedSnippet, setCopiedSnippet] = useState(false);

  // Hero Interactive Chat Widget State
  const [heroChat, setHeroChat] = useState([
    { role: 'bot', text: "Hi! I am your BlinkBot Assistant. Try clicking one of the questions below or type your own!" }
  ]);
  const [heroIsTyping, setHeroIsTyping] = useState(false);
  const [heroInput, setHeroInput] = useState('');

  // Feature scroll ref & FAQ state
  const featureScrollRef = useRef(null);
  const [openFaq, setOpenFaq] = useState(0);

  // Auto-scroll refs
  const sandboxScrollRef = useRef(null);
  const heroChatScrollRef = useRef(null);

  // Auto-scroll for Sandbox Chat
  useEffect(() => {
    if (sandboxScrollRef.current) {
      sandboxScrollRef.current.scrollTop = sandboxScrollRef.current.scrollHeight;
    }
  }, [simChatHistory, isSimTyping]);

  // Auto-scroll for Hero Demo Chat
  useEffect(() => {
    if (heroChatScrollRef.current) {
      heroChatScrollRef.current.scrollTop = heroChatScrollRef.current.scrollHeight;
    }
  }, [heroChat, heroIsTyping]);

  // Animated counter for hero stats
  const [statsVisible, setStatsVisible] = useState(false);
  const statsRef = useRef(null);

  // Navbar scroll state
  const [scrolled, setScrolled] = useState(false);

  // Scroll listener for navbar
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  // Stats visibility observer
  useEffect(() => {
    if (!statsRef.current) return;
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) setStatsVisible(true); },
      { threshold: 0.3 }
    );
    observer.observe(statsRef.current);
    return () => observer.disconnect();
  }, []);

  // Initialize Sandbox chat when persona changes
  useEffect(() => {
    const defaultQ = activePersona.questions[0];
    const defaultR = activePersona.responses[defaultQ];
    setSimChatHistory([
      { role: 'bot', text: `Hi! I'm your **${activePersona.name}**. Ask me anything about your documents!` },
      { role: 'user', text: defaultQ },
      { role: 'bot', text: defaultR.answer, sources: defaultR.sources },
    ]);
  }, [activePersona]);

  const handleQuestionClick = (questionText) => {
    if (isSimTyping) return;
    const updated = [...simChatHistory, { role: 'user', text: questionText }];
    setSimChatHistory(updated);
    setIsSimTyping(true);
    setTimeout(() => {
      const response = activePersona.responses[questionText] || {
        answer: "I searched your document index and found relevant context to answer your question accurately.",
        sources: ["Document_Index.pdf"],
      };
      setSimChatHistory([...updated, { role: 'bot', text: response.answer, sources: response.sources }]);
      setIsSimTyping(false);
    }, 700);
  };

  const handleHeroChatSend = (textToSend) => {
    if (!textToSend.trim() || heroIsTyping) return;
    const userMsg = { role: 'user', text: textToSend };
    const nextChat = [...heroChat, userMsg];
    setHeroChat(nextChat);
    setHeroIsTyping(true);
    setHeroInput('');

    // Transform chat history for the API payload
    const history = heroChat.map(msg => ({
      role: msg.role === 'bot' ? 'assistant' : 'user',
      content: msg.text
    }));

    let socketOpened = false;
    let streamedResponse = '';
    
    // Attempt real WebSocket connection to live chatbot
    const clientId = Math.random().toString(36).substring(7);
    const wsUrl = `wss://api.blinkbot.in/ws/widget/chat/${clientId}`;
    const ws = new WebSocket(wsUrl);

    // Timeout fallback if connection doesn't open in 2.5 seconds
    const fallbackTimeout = setTimeout(() => {
      if (!socketOpened) {
        try { ws.close(); } catch (e) {}
        triggerMockFallback();
      }
    }, 2500);

    const triggerMockFallback = () => {
      let botResponse = "That's a great question! BlinkBot is a zero-code platform that lets you build, route, and deploy custom AI agent teams in minutes. Let me know if you want to know about features!";
      const textLower = textToSend.toLowerCase();

      if (textLower.includes('deploy') || textLower.includes('website') || textLower.includes('embed')) {
        botResponse = "Deploying is simple: just copy your unique 1-line script tag from the dashboard and paste it into any website. It works instantly!";
      } else if (textLower.includes('whatsapp') || textLower.includes('sms') || textLower.includes('message') || textLower.includes('channel')) {
        botResponse = "Yes! You can connect your agents directly to WhatsApp, SMS, or custom API webhooks to automate sending messages and running background tasks.";
      } else if (textLower.includes('secure') || textLower.includes('privacy') || textLower.includes('data')) {
        botResponse = "Absolutely. Your data is kept 100% private and secure within your team's isolated workspace. We never share or use your proprietary documents to train public AI models.";
      } else if (textLower.includes('zero') || textLower.includes('code') || textLower.includes('minutes') || textLower.includes('create')) {
        botResponse = "BlinkBot is completely zero-code. Describe what you need in a single plain-English prompt, and our system automatically provisions your agents, links their knowledge, and configures their tools.";
      }

      setHeroChat([...nextChat, { role: 'bot', text: botResponse }]);
      setHeroIsTyping(false);
    };

    ws.onopen = () => {
      socketOpened = true;
      clearTimeout(fallbackTimeout);
      ws.send(JSON.stringify({
        type: 'chat_request',
        payload: {
          chatbot_id: '19802bcc-68a2-46c2-86fc-7e17049cfaa3',
          message: textToSend,
          history: history,
          language: 'en'
        }
      }));
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'text_chunk') {
          setHeroIsTyping(false);
          streamedResponse += data.content;
          setHeroChat([...nextChat, { role: 'bot', text: streamedResponse }]);
        } else if (data.type === 'stream_end') {
          ws.close();
        } else if (data.type === 'error') {
          console.warn("WS error payload:", data.content);
          ws.close();
          triggerMockFallback();
        }
      } catch (err) {
        console.error("WS message parse error:", err);
      }
    };

    ws.onerror = (err) => {
      console.warn("WS connection error:", err);
      clearTimeout(fallbackTimeout);
      try { ws.close(); } catch (e) {}
      if (!socketOpened) {
        triggerMockFallback();
      }
    };
  };

  const handleDemoSubmit = async (e) => {
    e.preventDefault();
    if (!demoForm.name.trim() || !demoForm.email.trim()) {
      toast.error("Please fill in your Name and Email.");
      return;
    }
    setIsSubmitting(true);
    try {
      const res = await fetch(`${API_URL}/api/demo-request`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(demoForm),
      });
      if (!res.ok) throw new Error('Failed');
      toast.success("Demo request sent! We'll reach out within 24 hours.");
      setDemoForm({ name: '', email: '', company: '', message: '' });
    } catch {
      toast.error("Couldn't submit right now. Please try again or email us directly.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const copyWidgetScript = () => {
    const script = `<script 
  src="https://blinkbot.in/widget.js" 
  data-chatbot-id="bot_demo_9823"
  data-color="${customWidgetColor}"
  data-position="${customWidgetPosition}"
  async>
</script>`;
    navigator.clipboard.writeText(script);
    setCopiedSnippet(true);
    toast.success("Script snippet copied to clipboard!");
    setTimeout(() => setCopiedSnippet(false), 2000);
  };

  const scrollFeatures = (direction) => {
    if (featureScrollRef.current) {
      featureScrollRef.current.scrollBy({ left: direction === 'left' ? -380 : 380, behavior: 'smooth' });
    }
  };

  const WIDGET_COLORS = ['#FF4D00', '#2563EB', '#10B981', '#7C3AED', '#EC4899', '#F59E0B'];

  return (
    <div className="min-h-screen bg-background text-foreground font-sans selection:bg-primary/20 overflow-x-hidden transition-colors duration-300">

      {/* ═══════════════════════════════════════════════════════════════════
          NAVIGATION
      ═══════════════════════════════════════════════════════════════════ */}
      <nav className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled
          ? 'bg-background/95 backdrop-blur-xl border-b border-border shadow-sm'
          : 'bg-transparent'
      }`}>
        <div className="flex items-center justify-between px-6 md:px-10 py-4 max-w-7xl mx-auto">
          <Logo />

          <div className="hidden md:flex items-center gap-7">
            {[
              { label: 'Features', href: '#features' },
              { label: 'Live Demo', href: '#sandbox' },
              { label: 'How It Works', href: '#how-it-works' },
              { label: 'Pricing', href: '#pricing' },
              { label: 'FAQ', href: '#faq' },
            ].map(({ label, href }) => (
              <a
                key={label}
                href={href}
                className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
              >
                {label}
              </a>
            ))}
            <a href="https://app.blinkbot.in/about" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
              About Us
            </a>
            <a href="https://app.blinkbot.in/user-guide" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
              User Documentation
            </a>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={toggleDarkMode}
              type="button"
              aria-label="Toggle theme"
              className="h-9 w-9 rounded-xl border border-border text-muted-foreground flex items-center justify-center hover:bg-muted hover:text-foreground transition-all cursor-pointer"
            >
              {darkMode ? <Sun size={16} className="text-amber-400" /> : <Moon size={16} />}
            </button>

            <a href="https://app.blinkbot.in/login" className="text-sm font-semibold hover:text-primary transition-colors hidden sm:inline px-3 py-2">
              Log in
            </a>

            <a
              href="https://app.blinkbot.in/login"
              className="btn-primary px-5 py-2.5 rounded-full text-sm font-bold shadow-md hover:shadow-lg hover:scale-[1.02] transition-all flex items-center gap-1.5"
            >
              <Zap size={14} /> Get Started Free
            </a>
          </div>
        </div>
      </nav>

      {/* ═══════════════════════════════════════════════════════════════════
          HERO SECTION
      ═══════════════════════════════════════════════════════════════════ */}
      <section className="relative pt-32 md:pt-40 pb-20 md:pb-28 px-6 overflow-hidden bg-background">
        {/* Animated background orbs */}
        <div className="absolute inset-0 pointer-events-none overflow-hidden">
          <div
            className="absolute top-[-10%] left-[10%] w-[600px] h-[600px] rounded-full opacity-[0.07] dark:opacity-[0.05] blur-[100px] animate-pulse"
            style={{ background: 'radial-gradient(circle, #FF4D00, transparent)' }}
          />
          <div
            className="absolute top-[20%] right-[-5%] w-[500px] h-[500px] rounded-full opacity-[0.05] dark:opacity-[0.04] blur-[120px] animate-pulse"
            style={{ background: 'radial-gradient(circle, #7C3AED, transparent)', animationDelay: '1s' }}
          />
          <div
            className="absolute bottom-[0%] left-[30%] w-[400px] h-[400px] rounded-full opacity-[0.04] dark:opacity-[0.03] blur-[100px]"
            style={{ background: 'radial-gradient(circle, #2563EB, transparent)' }}
          />
        </div>

        <div className="grid lg:grid-cols-12 gap-12 items-center max-w-7xl mx-auto w-full relative z-10 text-left">
          {/* Left Column: Text & CTAs */}
          <div className="lg:col-span-7 flex flex-col items-start">
            <span className="badge">Introducing BlinkBot 1.0</span>

            {/* Headline */}
            <h1 className="text-4xl sm:text-5xl md:text-6xl font-extrabold tracking-tight leading-[1.1] text-foreground">
              Empowering businesses to build{' '}
              <span className="relative inline-block">
                <span
                  className="bg-clip-text text-transparent animate-pulse"
                  style={{ backgroundImage: 'linear-gradient(135deg, #FF4D00 0%, #FF8C00 100%)' }}
                >
                  custom AI agents
                </span>
              </span>{' '}
              in minutes.
              <br />
              <span className="text-foreground/75 font-semibold text-2xl sm:text-3xl md:text-4xl mt-3 block">
                Zero coding required. Deploy them as a chatbot on your website instantly.
              </span>
            </h1>

            {/* Sub-headline */}
            <p className="mt-6 text-base sm:text-lg text-muted-foreground max-w-xl leading-relaxed">
              Connect any tools you want to automate your work. With just one plain-English prompt, deploy a secure agent team to handle your tasks, complete with manual approvals.
            </p>

            {/* CTAs */}
            <div className="mt-8 flex flex-col sm:flex-row items-center gap-4 w-full sm:w-auto">
              <a
                href="https://app.blinkbot.in/login"
                className="w-full sm:w-auto btn-primary px-8 py-3.5 rounded-full text-base font-bold shadow-lg hover:shadow-xl hover:scale-[1.03] transition-all flex items-center justify-center gap-2 group"
              >
                Start Building for Free
                <ArrowRight size={18} className="group-hover:translate-x-0.5 transition-transform" />
              </a>
              <a
                href="#sandbox"
                className="w-full sm:w-auto px-8 py-3.5 rounded-full text-base font-semibold border border-border bg-card hover:bg-muted transition-all flex items-center justify-center gap-2 shadow-xs"
              >
                <Play size={15} className="text-primary fill-primary" /> See It Live
              </a>
            </div>

            {/* Trust badges */}
            <div className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-3 text-xs text-muted-foreground font-medium">
              <div className="flex items-center gap-1.5">
                <CheckCircle2 size={14} className="text-emerald-500" />
                Free Starter Plan
              </div>
              <div className="flex items-center gap-1.5">
                <CheckCircle2 size={14} className="text-emerald-500" />
                No Credit Card Required
              </div>
              <div className="flex items-center gap-1.5">
                <CheckCircle2 size={14} className="text-emerald-500" />
                Omnichannel Tools
              </div>
            </div>
          </div>

          {/* Right Column: Premium Interactive Chat Widget Mockup */}
          <div className="lg:col-span-5 relative w-full flex justify-center">
            <div className="w-full max-w-md bg-card/75 backdrop-blur-md border border-border/80 rounded-3xl p-5 shadow-xl relative overflow-hidden flex flex-col gap-3 min-h-[380px]">
              {/* Window Header */}
              <div className="flex items-center justify-between border-b border-border/40 pb-3">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center border border-primary/20 text-primary">
                    <Bot size={18} />
                  </div>
                  <div>
                    <div className="text-xs font-bold text-foreground">BlinkBot Assistant</div>
                    <div className="flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                      <span className="text-[10px] text-muted-foreground font-medium">Online</span>
                    </div>
                  </div>
                </div>
                <div className="text-[10px] font-mono text-muted-foreground bg-muted/40 px-2 py-0.5 rounded border border-border/30">
                  Demo Chat
                </div>
              </div>

              {/* Chat Messages Area */}
              <div ref={heroChatScrollRef} className="flex-1 overflow-y-auto max-h-[200px] flex flex-col gap-2.5 pr-1" style={{ scrollbarWidth: 'none' }}>
                {heroChat.map((msg, i) => (
                  <div
                    key={i}
                    className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`text-xs rounded-2xl px-3.5 py-2 max-w-[80%] leading-relaxed ${
                        msg.role === 'user'
                          ? 'bg-primary text-white rounded-br-xs'
                          : 'bg-muted/75 text-foreground rounded-bl-xs'
                      }`}
                    >
                      {msg.role === 'bot' ? (
                        <div dangerouslySetInnerHTML={{ __html: formatMarkdown(msg.text) }} />
                      ) : (
                        msg.text
                      )}
                    </div>
                  </div>
                ))}

                {/* Typing Indicator */}
                {heroIsTyping && (
                  <div className="flex justify-start">
                    <div className="bg-muted/75 text-muted-foreground text-xs rounded-2xl rounded-bl-xs px-3.5 py-2 flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground/60 animate-bounce"></span>
                      <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground/60 animate-bounce [animation-delay:0.2s]"></span>
                      <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground/60 animate-bounce [animation-delay:0.4s]"></span>
                    </div>
                  </div>
                )}
              </div>

              {/* Suggested Questions */}
              <div className="flex flex-wrap gap-1.5 pt-2">
                {[
                  "How to deploy?",
                  "Do you support WhatsApp?",
                  "Is it secure?"
                ].map((q) => (
                  <button
                    key={q}
                    type="button"
                    onClick={() => handleHeroChatSend(q)}
                    className="text-[10px] font-semibold bg-muted hover:bg-muted/80 text-foreground border border-border/80 px-2.5 py-1 rounded-full transition-all cursor-pointer"
                  >
                    {q}
                  </button>
                ))}
              </div>

              {/* Input Footer */}
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  handleHeroChatSend(heroInput);
                }}
                className="flex items-center gap-1.5 border-t border-border/40 pt-3"
              >
                <input
                  type="text"
                  value={heroInput}
                  onChange={(e) => setHeroInput(e.target.value)}
                  placeholder="Type a question..."
                  className="flex-1 bg-muted/50 border border-border/60 rounded-xl px-3 py-2 text-xs text-foreground focus:outline-none focus:border-primary/50 placeholder:text-muted-foreground/60"
                />
                <button
                  type="submit"
                  disabled={!heroInput.trim() || heroIsTyping}
                  className="h-8 w-8 rounded-xl bg-primary hover:bg-primary/90 text-white flex items-center justify-center transition-all disabled:opacity-50 cursor-pointer"
                >
                  <Send size={12} />
                </button>
              </form>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════
          STATS STRIP
      ═══════════════════════════════════════════════════════════════════ */}
      <section ref={statsRef} className="py-14 border-y border-border bg-card">
        <div className="max-w-5xl mx-auto px-6 grid grid-cols-2 md:grid-cols-4 gap-8">
          {STATS.map(({ value, label, icon: Icon }) => (
            <div key={label} className="flex flex-col items-center text-center gap-3">
              <div className="w-12 h-12 rounded-2xl bg-primary/10 flex items-center justify-center">
                <Icon size={22} className="text-primary" />
              </div>
              <div
                className={`text-3xl md:text-4xl font-black text-foreground transition-all duration-700 ${
                  statsVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-3'
                }`}
              >
                {value}
              </div>
              <div className="text-xs text-muted-foreground font-medium leading-snug">{label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════
          WHY BLINKBOT — PAIN POINTS
      ═══════════════════════════════════════════════════════════════════ */}
      <section className="py-20 md:py-28 px-6">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-14">
            <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-rose-500/10 text-rose-500 text-xs font-bold uppercase tracking-wider mb-4">
              <AlertCircle size={13} /> Sound Familiar?
            </div>
            <h2 className="text-3xl md:text-5xl font-extrabold tracking-tight text-foreground">
              We've all been there.
            </h2>
            <p className="mt-4 text-muted-foreground text-base max-w-xl mx-auto">
              These are the real problems teams face before they discover BlinkBot.
            </p>
          </div>

          <div className="space-y-5">
            {PAIN_POINTS.map(({ pain, solve, icon: Icon }, i) => (
              <div
                key={i}
                className="bg-card border border-border rounded-2xl p-6 md:p-8 grid md:grid-cols-2 gap-6 items-center hover:border-primary/20 transition-colors group"
              >
                <div className="flex gap-4 items-start">
                  <div className="w-10 h-10 rounded-xl bg-rose-500/10 flex items-center justify-center shrink-0 mt-0.5">
                    <Icon size={18} className="text-rose-500" />
                  </div>
                  <div>
                    <div className="text-xs font-bold uppercase tracking-wider text-rose-500 mb-1.5">The Problem</div>
                    <p className="text-sm text-foreground leading-relaxed font-medium">{pain}</p>
                  </div>
                </div>
                <div className="flex gap-4 items-start">
                  <div className="w-10 h-10 rounded-xl bg-emerald-500/10 flex items-center justify-center shrink-0 mt-0.5">
                    <CheckCircle2 size={18} className="text-emerald-500" />
                  </div>
                  <div>
                    <div className="text-xs font-bold uppercase tracking-wider text-emerald-500 mb-1.5">BlinkBot Fixes It</div>
                    <p className="text-sm text-foreground leading-relaxed font-medium">{solve}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════
          HOW IT WORKS
      ═══════════════════════════════════════════════════════════════════ */}
      <section id="how-it-works" className="py-20 md:py-28 bg-card border-y border-border px-6">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-primary/10 text-primary text-xs font-bold uppercase tracking-wider mb-4">
              <Rocket size={13} /> How It Works
            </div>
            <h2 className="text-3xl md:text-5xl font-extrabold tracking-tight text-foreground">
              From zero to live AI assistant
              <br />
              <span className="text-primary">in under 10 minutes.</span>
            </h2>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {HOW_IT_WORKS.map(({ step, icon: Icon, title, desc, accent, iconColor, iconBg }, i) => (
              <div key={step} className="relative">
                {/* Connector line */}
                {i < HOW_IT_WORKS.length - 1 && (
                  <div className="hidden md:block absolute top-10 left-[calc(100%_-_16px)] w-8 h-px border-t-2 border-dashed border-border z-10" />
                )}

                <div className={`bg-gradient-to-br ${accent} border border-border rounded-[24px] p-7 h-full transition-all hover:-translate-y-1 hover:shadow-lg`}>
                  <div className="flex items-center gap-4 mb-5">
                    <div className={`w-14 h-14 rounded-2xl ${iconBg} flex items-center justify-center`}>
                      <Icon size={26} className={iconColor} />
                    </div>
                    <span className="text-5xl font-black text-foreground/10 font-mono leading-none">{step}</span>
                  </div>
                  <h3 className="text-xl font-bold text-foreground mb-3">{title}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">{desc}</p>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-12 text-center">
            <a
              href="https://app.blinkbot.in/login"
              className="inline-flex items-center gap-2 btn-primary px-8 py-4 rounded-full text-base font-bold shadow-lg hover:shadow-xl hover:scale-[1.03] transition-all"
            >
              Try It Right Now for Free <ArrowRight size={18} />
            </a>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════
          FEATURE CARDS CAROUSEL
      ═══════════════════════════════════════════════════════════════════ */}
      <section id="features" className="py-20 md:py-28 px-6 max-w-7xl mx-auto">
        <div className="flex flex-col md:flex-row items-start md:items-end justify-between mb-12 gap-4">
          <div>
            <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-primary/10 text-primary text-xs font-bold uppercase tracking-wider mb-3">
              <Layers size={13} /> Everything You Need
            </div>
            <h2 className="text-3xl md:text-5xl font-extrabold tracking-tight text-foreground">
              Platform Features
            </h2>
            <p className="mt-3 text-muted-foreground text-base max-w-md">
              A complete toolkit for building, deploying, and managing AI assistants at any scale.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => scrollFeatures('left')}
              className="h-11 w-11 rounded-2xl bg-card border border-border flex items-center justify-center text-foreground hover:bg-primary hover:text-white hover:border-primary transition-all shadow-xs cursor-pointer"
              aria-label="Previous"
            >
              <ChevronLeft size={20} />
            </button>
            <button
              onClick={() => scrollFeatures('right')}
              className="h-11 w-11 rounded-2xl bg-card border border-border flex items-center justify-center text-foreground hover:bg-primary hover:text-white hover:border-primary transition-all shadow-xs cursor-pointer"
              aria-label="Next"
            >
              <ChevronRight size={20} />
            </button>
          </div>
        </div>

        <div
          ref={featureScrollRef}
          className="flex gap-5 overflow-x-auto py-4 px-1"
          style={{ scrollbarWidth: 'none', msOverflowStyle: 'none', scrollSnapType: 'x mandatory' }}
        >
          {FEATURE_CARDS.map(({ icon: Icon, title, badge, desc, gradient, borderHover, iconBg, iconColor }) => (
            <div
              key={title}
              style={{ scrollSnapAlign: 'start' }}
              className={`w-[300px] sm:w-[340px] shrink-0 bg-gradient-to-br ${gradient} border border-border rounded-[24px] p-7 ${borderHover} hover:shadow-lg transition-all duration-300 flex flex-col gap-5`}
            >
              <div className="flex items-center justify-between">
                <div className={`w-12 h-12 rounded-2xl ${iconBg} flex items-center justify-center`}>
                  <Icon size={23} className={iconColor} />
                </div>
                <span className="text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-full bg-card text-muted-foreground border border-border">
                  {badge}
                </span>
              </div>
              <div>
                <h3 className="text-lg font-bold mb-2 text-foreground">{title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════
          SUPPORTED LLM PROVIDERS STRIP
      ═══════════════════════════════════════════════════════════════════ */}
      <section className="py-16 border-y border-border bg-card px-6">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-10">
            <div className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-1">
              Supported LLM Providers & Embedding Engines
            </div>
            <p className="text-sm text-muted-foreground">Bring your own key. Switch models anytime. No lock-in.</p>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
             {LLM_PROVIDERS.map((provider, i) => (
              <div
                key={i}
                className="p-5 rounded-2xl bg-background border border-border text-center transition-all hover:-translate-y-1 hover:shadow-md hover:border-primary/30 cursor-default"
              >
                <div className="font-bold text-sm text-foreground mb-1">{provider.name}</div>
                <div className="text-[11px] font-semibold text-primary mb-1.5">{provider.badge}</div>
                <div className="text-[10px] text-muted-foreground leading-tight">{provider.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════
          INTERACTIVE SANDBOX
      ═══════════════════════════════════════════════════════════════════ */}
      <section id="sandbox" className="py-20 md:py-28 px-6">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-primary/10 text-primary text-xs font-bold uppercase tracking-wider mb-4">
              <Terminal size={13} /> Interactive Live Sandbox
            </div>
            <h2 className="text-3xl md:text-5xl font-extrabold tracking-tight text-foreground">
              Test-drive the agent teams.
              <br />
              See how they respond.
            </h2>
            <p className="mt-4 text-muted-foreground text-base max-w-2xl mx-auto">
              These are live demo agents designed to showcase how specialized teams retrieve knowledge and handle tasks in real-time. Try asking them a question below.
            </p>
          </div>

          {/* Persona Switcher */}
          <div className="flex flex-wrap items-center justify-center gap-3 mb-8">
            {DEMO_PERSONAS.map((persona) => (
              <button
                key={persona.id}
                onClick={() => setActivePersona(persona)}
                className={`flex items-center gap-2.5 px-5 py-3 rounded-2xl text-sm font-bold transition-all cursor-pointer ${
                  activePersona.id === persona.id
                    ? 'bg-primary text-white shadow-md scale-105'
                    : 'bg-card border border-border text-muted-foreground hover:text-foreground hover:border-primary/30'
                }`}
              >
                <persona.icon size={16} />
                {persona.name}
              </button>
            ))}
          </div>

          {/* Simulator Box */}
          <div className="bg-background border border-border rounded-[28px] shadow-xl overflow-hidden">
            {/* Header */}
            <div className="px-6 py-4 border-b border-border bg-muted/30 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`w-10 h-10 rounded-xl ${activePersona.avatarBg} flex items-center justify-center text-white shadow-xs`}>
                  <activePersona.icon size={20} />
                </div>
                <div>
                  <div className="font-bold text-sm flex items-center gap-2 text-foreground">
                    {activePersona.name}
                    <span className="text-[10px] bg-primary/10 text-primary font-semibold px-2 py-0.5 rounded-full">
                      {activePersona.badge}
                    </span>
                  </div>
                  <div className="text-xs text-muted-foreground">{activePersona.docsCount}</div>
                </div>
              </div>
            </div>

            {/* Chat Messages */}
            <div ref={sandboxScrollRef} className="p-6 md:p-8 space-y-4 min-h-[300px] max-h-[400px] overflow-y-auto bg-card">
              {simChatHistory.map((msg, idx) => (
                <div
                  key={idx}
                  className={`flex gap-3 items-start animate-message ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
                >
                  <div className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 text-xs font-bold ${
                    msg.role === 'user' ? 'bg-blue-600 text-white' : `${activePersona.avatarBg} text-white`
                  }`}>
                    {msg.role === 'user' ? 'You' : <Bot size={15} />}
                  </div>

                  <div className={`p-4 rounded-2xl max-w-[80%] text-sm leading-relaxed ${
                    msg.role === 'user'
                      ? 'bg-blue-600/10 border border-blue-500/20 text-foreground rounded-tr-xs'
                      : 'bg-background border border-border text-foreground shadow-xs rounded-tl-xs'
                  }`}>
                    <p>{msg.text}</p>
                    {msg.sources && msg.sources.length > 0 && (
                      <div className="mt-3 pt-2.5 border-t border-border flex flex-wrap gap-1.5 items-center">
                        <span className="text-[11px] font-semibold text-muted-foreground flex items-center gap-1">
                          <FileText size={11} className="text-primary" /> Cited Sources:
                        </span>
                        {msg.sources.map((src, sIdx) => (
                          <span key={sIdx} className="text-[10px] font-semibold bg-primary/10 text-primary px-2.5 py-0.5 rounded-md border border-primary/20">
                            {src}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {isSimTyping && (
                <div className="flex gap-3 items-center text-xs text-muted-foreground bg-muted/40 p-3 rounded-2xl max-w-[200px]">
                  <Loader2 size={15} className="animate-spin text-primary" />
                  Querying vectors...
                </div>
              )}
            </div>

            {/* Prompt Suggestions */}
            <div className="p-4 border-t border-border bg-muted/20">
              <div className="text-xs font-semibold text-muted-foreground mb-2.5 flex items-center gap-1.5">
                <Lightbulb size={13} className="text-amber-500" />
                Try a sample question:
              </div>
              <div className="flex flex-wrap gap-2">
                {activePersona.questions.map((q, qIdx) => (
                  <button
                    key={qIdx}
                    onClick={() => handleQuestionClick(q)}
                    disabled={isSimTyping}
                    className="text-xs bg-card hover:bg-muted border border-border text-foreground px-3.5 py-2 rounded-xl transition-all text-left flex items-center gap-1.5 shadow-xs disabled:opacity-50 hover:border-primary/30 cursor-pointer"
                  >
                    "{q}" <ChevronRight size={12} className="text-muted-foreground" />
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════
          WIDGET CONFIGURATOR
      ═══════════════════════════════════════════════════════════════════ */}
      <section id="widget" className="py-20 md:py-28 bg-card border-y border-border px-6">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-14">
            <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-amber-500/10 text-amber-500 text-xs font-bold uppercase tracking-wider mb-4">
              <Sliders size={13} /> Widget Configurator
            </div>
            <h2 className="text-3xl md:text-5xl font-extrabold tracking-tight text-foreground">
              Your brand. Your bot.
            </h2>
            <p className="mt-4 text-muted-foreground text-base max-w-2xl mx-auto">
              Customize the accent color, header title, and screen position. The script snippet updates instantly, just copy and paste.
            </p>
          </div>

          <div className="grid lg:grid-cols-12 gap-8 items-stretch">
            {/* Controls Panel */}
            <div className="lg:col-span-5 bg-background border border-border rounded-[24px] p-7 space-y-7 shadow-lg">
              <div>
                <label className="text-sm font-semibold block mb-2.5 text-foreground">Widget Header Title</label>
                <input
                  type="text"
                  value={customWidgetTitle}
                  onChange={(e) => setCustomWidgetTitle(e.target.value)}
                  className="w-full border border-border bg-card rounded-xl px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-primary/30 text-foreground placeholder:text-muted-foreground"
                  placeholder="BlinkBot Assistant"
                />
              </div>

              <div>
                <label className="text-sm font-semibold block mb-3 text-foreground">Brand Accent Color</label>
                <div className="flex items-center gap-2.5">
                  {WIDGET_COLORS.map((color) => (
                    <button
                      key={color}
                      onClick={() => setCustomWidgetColor(color)}
                      style={{ backgroundColor: color }}
                      className={`w-9 h-9 rounded-full border-2 transition-all cursor-pointer ${
                        customWidgetColor === color ? 'scale-125 border-foreground shadow-md' : 'border-transparent hover:scale-110'
                      }`}
                    />
                  ))}
                  <input
                    type="color"
                    value={customWidgetColor}
                    onChange={(e) => setCustomWidgetColor(e.target.value)}
                    className="w-9 h-9 rounded-full border border-border cursor-pointer bg-transparent"
                    title="Custom color"
                  />
                </div>
              </div>

              <div>
                <label className="text-sm font-semibold block mb-3 text-foreground">Screen Position</label>
                <div className="grid grid-cols-2 gap-3">
                  {['right', 'left'].map((pos) => (
                    <button
                      key={pos}
                      onClick={() => setCustomWidgetPosition(pos)}
                      className={`py-3 px-4 rounded-xl text-xs font-semibold border transition-all capitalize cursor-pointer ${
                        customWidgetPosition === pos
                          ? 'bg-primary text-white border-primary shadow-sm'
                          : 'bg-card border-border hover:bg-muted text-foreground'
                      }`}
                    >
                      Bottom {pos}
                    </button>
                  ))}
                </div>
              </div>

              {/* Script Snippet */}
              <div>
                <div className="flex items-center justify-between text-xs font-semibold mb-2.5">
                  <span className="text-muted-foreground flex items-center gap-1.5">
                    <Code size={13} /> Generated HTML Snippet
                  </span>
                  <button
                    onClick={copyWidgetScript}
                    className="text-primary hover:underline flex items-center gap-1 font-bold cursor-pointer"
                  >
                    {copiedSnippet ? <Check size={13} className="text-emerald-500" /> : <Copy size={13} />}
                    {copiedSnippet ? 'Copied!' : 'Copy Code'}
                  </button>
                </div>
                <div className="bg-slate-950 text-slate-300 p-4 rounded-xl text-xs font-mono overflow-x-auto leading-loose border border-slate-800">
                  <code>
                    <span className="text-slate-500">{'<'}script</span><br />
                    <span className="pl-4">src=<span className="text-amber-400">"https://blinkbot.in/widget.js"</span></span><br />
                    <span className="pl-4">data-chatbot-id=<span className="text-amber-400">"bot_demo_9823"</span></span><br />
                    <span className="pl-4">data-color=<span className="text-amber-400">"{customWidgetColor}"</span></span><br />
                    <span className="pl-4">data-position=<span className="text-amber-400">"{customWidgetPosition}"</span> async{'>'}</span><br />
                    <span className="text-slate-500">{'<'}/script{'>'}</span>
                  </code>
                </div>
              </div>
            </div>

            {/* Live Widget Preview */}
            <div className="lg:col-span-7 flex flex-col items-center justify-center relative min-h-[480px] bg-background border border-border rounded-[28px] p-8 shadow-xl">
              {/* Mock browser bg */}
              <div className="absolute inset-0 rounded-[28px] overflow-hidden opacity-30 dark:opacity-10">
                <div className="absolute inset-0" style={{
                  backgroundImage: `radial-gradient(circle at 20px 20px, var(--border) 1px, transparent 0)`,
                  backgroundSize: '32px 32px'
                }} />
              </div>

              <div className="text-xs text-muted-foreground font-semibold mb-6 flex items-center gap-1.5 relative z-10">
                <Eye size={13} className="text-primary" /> Live Widget Preview
              </div>

              <div className="relative z-10 w-full max-w-xs">
                {/* Chat widget */}
                <div className="bg-background border border-border rounded-2xl shadow-2xl overflow-hidden transition-all duration-300">
                  <div style={{ backgroundColor: customWidgetColor }} className="p-4 text-white flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-full bg-white/20 flex items-center justify-center">
                        <Bot size={18} className="text-white" />
                      </div>
                      <div>
                        <div className="font-bold text-sm">{customWidgetTitle || 'BlinkBot'}</div>
                        <div className="text-[11px] opacity-80">Online · Powered by BlinkBot</div>
                      </div>
                    </div>
                    <div className="flex gap-1">
                      <div className="w-2 h-2 rounded-full bg-white/40" />
                      <div className="w-2 h-2 rounded-full bg-white/40" />
                      <div className="w-2 h-2 rounded-full bg-white/40" />
                    </div>
                  </div>

                  <div className="p-4 space-y-3 min-h-[200px] bg-card text-xs">
                    <div className="bg-background border border-border p-3 rounded-xl max-w-[85%] text-foreground leading-relaxed">
                      Hello! How can I help you with your knowledge base today?
                    </div>
                    <div className="p-3 rounded-xl max-w-[85%] ml-auto text-right text-foreground leading-relaxed" style={{ backgroundColor: `${customWidgetColor}18`, borderColor: `${customWidgetColor}33`, border: '1px solid' }}>
                      Which AI models are supported?
                    </div>
                    <div className="bg-background border border-border p-3 rounded-xl max-w-[90%] text-foreground leading-relaxed">
                      We support OpenRouter, OpenAI, Groq, Anthropic Claude, Google Gemini, and HuggingFace!
                    </div>
                  </div>

                  <div className="p-3 border-t border-border bg-background flex items-center gap-2">
                    <div className="flex-1 bg-muted/50 rounded-xl px-3 py-2 text-[10px] text-muted-foreground">
                      Type a message...
                    </div>
                    <button
                      style={{ backgroundColor: customWidgetColor }}
                      className="w-8 h-8 rounded-xl flex items-center justify-center text-white shrink-0"
                    >
                      <Send size={13} />
                    </button>
                  </div>
                </div>

                {/* Widget trigger button */}
                <div className={`absolute -bottom-4 ${customWidgetPosition === 'right' ? '-right-4' : '-left-4'} transition-all duration-300`}>
                  <button
                    style={{ backgroundColor: customWidgetColor }}
                    className="w-13 h-13 rounded-full shadow-xl flex items-center justify-center text-white hover:scale-110 transition-transform cursor-pointer"
                  >
                    <MessageSquare size={22} />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════
          PRICING
      ═══════════════════════════════════════════════════════════════════ */}
      <section id="pricing" className="py-20 md:py-28 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-12">
            <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-amber-500/10 text-amber-500 text-xs font-bold uppercase tracking-wider mb-4">
              <Star size={13} /> Pricing
            </div>
            <h2 className="text-3xl md:text-5xl font-extrabold tracking-tight text-foreground">
              Simple, transparent pricing.
            </h2>
            <p className="mt-4 text-muted-foreground text-base max-w-xl mx-auto">
              Start for free, with no credit card needed. Scale up only when your team needs more.
            </p>

            {/* Billing Toggle */}
            <div className="flex items-center justify-center gap-4 mt-8">
              <span className={`text-sm font-semibold ${!annualBilling ? 'text-foreground' : 'text-muted-foreground'}`}>Monthly</span>
              <button
                type="button"
                onClick={() => setAnnualBilling(!annualBilling)}
                className={`w-12 h-6 rounded-full transition-colors relative flex items-center p-0.5 cursor-pointer ${annualBilling ? 'bg-primary' : 'bg-muted'}`}
              >
                <span className={`w-5 h-5 rounded-full bg-white shadow-sm transition-transform ${annualBilling ? 'translate-x-6' : 'translate-x-0'}`} />
              </button>
              <span className={`text-sm font-semibold flex items-center gap-2 ${annualBilling ? 'text-foreground' : 'text-muted-foreground'}`}>
                Annual
                <span className="bg-emerald-500/10 text-emerald-500 text-xs font-bold px-2.5 py-0.5 rounded-full border border-emerald-500/20">
                  Save 20%
                </span>
              </span>
            </div>
          </div>

          {/* Pricing Cards */}
          <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
            <PricingCard
              title="Starter"
              priceInr="0"
              priceUsd="0"
              desc="Free hook — perfect for testing and building your first AI Agent."
              features={[
                "1 Active Workspace",
                "1 AI Agent per Workspace",
                "500 AI Messages / month",
                "5 MB Document & Asset Storage",
                "Platform-managed system models only",
                "BYOK: Not Allowed",
                "Community Support"
              ]}
            />
            <PricingCard
              title="Pro"
              priceInr={annualBilling ? "559" : "699"}
              priceUsd={annualBilling ? "7" : "8"}
              desc="For growing teams & small businesses."
              features={[
                "1 Active Workspace",
                "5 AI Agents per Workspace",
                "10,000 AI Messages / month",
                "1 GB Vector & Asset Storage",
                "1 Embedded Website Chatbots",
                "BYOK: Allowed",
                "Granular Studio & Model Permissions",
                "Priority Support"
              ]}
              isPopular
            />
            <PricingCard
              title="Business"
              priceInr={annualBilling ? "1,599" : "1,999"}
              priceUsd={annualBilling ? "19" : "24"}
              desc="For agencies & scaling applications."
              features={[
                "Unlimited Workspaces",
                "Unlimited AI Agents per Workspace",
                "50,000 AI Messages / month",
                "10 GB Vector & Asset Storage",
                "Unlimited Embedded Chatbots",
                "BYOK: Allowed",
                "Full Audit Logging & RBAC Controls",
                "Dedicated Support Manager"
              ]}
            />
          </div>

          {/* Top-up Credits */}
          <div className="mt-10 max-w-3xl mx-auto bg-card border border-border rounded-2xl p-6 sm:p-8 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-5 shadow-md">
            <div>
              <div className="font-bold text-base text-foreground flex items-center gap-2">
                <Zap size={17} className="text-amber-500 fill-amber-500" />
                Non-Expiring Message Credit Top-Ups
              </div>
              <p className="text-xs text-muted-foreground mt-1.5 leading-relaxed">
                Run out of messages? Grab a top-up anytime: <strong>+5,000 messages</strong> for ₹299 ($4) 
                or <strong>+20,000 messages</strong> for ₹899 ($11). Credits never expire.
              </p>
            </div>
            <a
              href="https://app.blinkbot.in/login"
              className="px-5 py-2.5 rounded-xl btn-primary text-xs font-bold shrink-0 shadow-md whitespace-nowrap"
            >
              View Billing →
            </a>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════
          FAQ
      ═══════════════════════════════════════════════════════════════════ */}
      <section id="faq" className="py-20 md:py-28 bg-card border-y border-border px-6">
        <div className="max-w-3xl mx-auto">
          <div className="text-center mb-14">
            <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-blue-500/10 text-blue-500 text-xs font-bold uppercase tracking-wider mb-4">
              <HelpCircle size={13} /> FAQ
            </div>
            <h2 className="text-3xl md:text-5xl font-extrabold tracking-tight text-foreground">
              Questions? We've got answers.
            </h2>
          </div>

          <div className="space-y-3">
            {FAQS.map((faq, idx) => (
              <div key={idx} className="bg-background border border-border rounded-2xl overflow-hidden transition-all shadow-xs">
                <button
                  onClick={() => setOpenFaq(openFaq === idx ? null : idx)}
                  className="w-full px-6 py-5 text-left font-bold text-base flex items-center justify-between gap-4 text-foreground hover:text-primary transition-colors cursor-pointer"
                >
                  <span>{faq.q}</span>
                  <ChevronDown
                    size={17}
                    className={`transition-transform duration-200 text-muted-foreground shrink-0 ${openFaq === idx ? 'rotate-180 text-primary' : ''}`}
                  />
                </button>
                {openFaq === idx && (
                  <div className="px-6 pb-6 text-sm text-muted-foreground leading-relaxed border-t border-border pt-4 bg-card/30">
                    {faq.a}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════
          BOOK A DEMO FORM
      ═══════════════════════════════════════════════════════════════════ */}
      <section id="demo" className="py-20 md:py-28 px-6">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-12">
            <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-primary/10 text-primary text-xs font-bold uppercase tracking-wider mb-4">
              <MessagesSquare size={13} /> Talk to Us
            </div>
            <h2 className="text-3xl md:text-5xl font-extrabold tracking-tight text-foreground">
              Need something custom?
            </h2>
            <p className="mt-4 text-muted-foreground text-base max-w-xl mx-auto">
              Have high-volume requirements, custom integrations, or want a guided walkthrough? 
              Drop us a message and we'll get back to you within 24 hours.
            </p>
          </div>

          <form
            onSubmit={handleDemoSubmit}
            className="bg-card border border-border rounded-[28px] p-7 md:p-10 shadow-xl space-y-6"
          >
            <div className="grid sm:grid-cols-2 gap-5">
              <div>
                <label className="text-sm font-semibold block mb-2 text-foreground">
                  Full Name <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  value={demoForm.name}
                  onChange={(e) => setDemoForm({ ...demoForm, name: e.target.value })}
                  className="w-full border border-border bg-background rounded-xl px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-primary/30 text-foreground placeholder:text-muted-foreground"
                  placeholder="Your full name"
                  required
                />
              </div>
              <div>
                <label className="text-sm font-semibold block mb-2 text-foreground">
                  Work Email <span className="text-rose-500">*</span>
                </label>
                <input
                  type="email"
                  value={demoForm.email}
                  onChange={(e) => setDemoForm({ ...demoForm, email: e.target.value })}
                  className="w-full border border-border bg-background rounded-xl px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-primary/30 text-foreground placeholder:text-muted-foreground"
                  placeholder="you@company.com"
                  required
                />
              </div>
            </div>

            <div>
              <label className="text-sm font-semibold block mb-2 text-foreground">Company / Organization</label>
              <input
                type="text"
                value={demoForm.company}
                onChange={(e) => setDemoForm({ ...demoForm, company: e.target.value })}
                className="w-full border border-border bg-background rounded-xl px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-primary/30 text-foreground placeholder:text-muted-foreground"
                placeholder="Acme Corp"
              />
            </div>

            <div>
              <label className="text-sm font-semibold block mb-2 text-foreground">
                Tell us about your needs
              </label>
              <textarea
                rows={4}
                value={demoForm.message}
                onChange={(e) => setDemoForm({ ...demoForm, message: e.target.value })}
                className="w-full border border-border bg-background rounded-xl px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-primary/30 resize-y text-foreground placeholder:text-muted-foreground"
                placeholder="Describe your use case, document volumes, or integration requirements..."
              />
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full btn-primary py-4 rounded-xl text-base font-bold shadow-lg hover:shadow-xl flex items-center justify-center gap-2.5 transition-all disabled:opacity-75 cursor-pointer"
            >
              {isSubmitting ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
              {isSubmitting ? "Sending your request..." : "Send Message"}
            </button>
          </form>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════
          FINAL CTA BANNER
      ═══════════════════════════════════════════════════════════════════ */}
      <section className="py-20 md:py-28 px-6 bg-card border-t border-border">
        <div className="max-w-4xl mx-auto text-center relative">
          {/* Background glow */}
          <div
            className="absolute inset-0 blur-[80px] opacity-10 dark:opacity-5 pointer-events-none"
            style={{ background: 'radial-gradient(circle, #FF4D00, transparent)' }}
          />

          <div className="relative z-10">
            <h2 className="text-4xl md:text-6xl font-extrabold tracking-tight text-foreground leading-tight">
              Your workflow tasks are just
              <br />
              <span
                className="bg-clip-text text-transparent"
                style={{ backgroundImage: 'linear-gradient(135deg, #FF4D00 0%, #FF8C00 100%)' }}
              >
                waiting to be automated.
              </span>
            </h2>

            <p className="mt-6 text-lg text-muted-foreground max-w-xl mx-auto leading-relaxed">
              Turn your business processes into secure, automated AI agent teams that run tools, connect systems, and deploy in minutes. Completely zero-code.
            </p>

            <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
              <a
                href="https://app.blinkbot.in/login"
                className="w-full sm:w-auto btn-primary px-10 py-4 rounded-full text-base font-bold shadow-lg hover:shadow-xl hover:scale-[1.03] transition-all flex items-center justify-center gap-2 group"
              >
                <Rocket size={18} />
                Build Your AI Agent Team for Free
                <ArrowRight size={18} className="group-hover:translate-x-0.5 transition-transform" />
              </a>
            </div>

            <p className="mt-5 text-xs text-muted-foreground">
              No credit card required · Free Starter plan included · Set up in minutes
            </p>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════
          FOOTER
      ═══════════════════════════════════════════════════════════════════ */}
      <footer className="border-t border-border bg-background">
        <div className="max-w-7xl mx-auto px-6 md:px-8 py-16">
          <div className="grid md:grid-cols-4 gap-10 md:gap-16">
            <div className="md:col-span-1 space-y-4">
              <Logo />
              <p className="text-sm text-muted-foreground leading-relaxed">
                Build, train, and deploy private AI assistants grounded in your own documents. No-code. No lock-in.
              </p>
            </div>

            <div>
              <h4 className="font-bold text-sm uppercase tracking-wider mb-5 text-foreground">Platform</h4>
              <ul className="space-y-3 text-sm text-muted-foreground">
                <li><a href="#features" className="hover:text-primary transition-colors">Features</a></li>
                <li><a href="#sandbox" className="hover:text-primary transition-colors">Live Sandbox</a></li>
                <li><a href="#widget" className="hover:text-primary transition-colors">Widget Generator</a></li>
                <li><a href="#pricing" className="hover:text-primary transition-colors">Pricing</a></li>
              </ul>
            </div>

            <div>
              <h4 className="font-bold text-sm uppercase tracking-wider mb-5 text-foreground">Resources</h4>
              <ul className="space-y-3 text-sm text-muted-foreground">
                <li><a href="https://app.blinkbot.in/user-guide" className="hover:text-primary transition-colors">User Documentation</a></li>
                <li><a href="https://app.blinkbot.in/blog" className="hover:text-primary transition-colors">Product Blog</a></li>
                <li><a href="https://app.blinkbot.in/login" className="hover:text-primary transition-colors">Studio Console</a></li>
              </ul>
            </div>

            <div>
              <h4 className="font-bold text-sm uppercase tracking-wider mb-5 text-foreground">Company</h4>
              <ul className="space-y-3 text-sm text-muted-foreground">
                <li><a href="https://app.blinkbot.in/about" className="hover:text-primary transition-colors">About Us</a></li>
                <li><a href="https://app.blinkbot.in/terms" className="hover:text-primary transition-colors">Terms of Service</a></li>
                <li><a href="mailto:blinkbot07@gmail.com" className="hover:text-primary transition-colors">Contact Support</a></li>
              </ul>
            </div>
          </div>

          <div className="border-t border-border mt-12 pt-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-muted-foreground">
            <p>© {new Date().getFullYear()} BlinkBot. All rights reserved.</p>
            <div className="flex items-center gap-6 font-medium">
              <a href="https://app.blinkbot.in/terms" className="hover:text-primary transition-colors">Privacy & Terms</a>
              <a href="https://app.blinkbot.in/about" className="hover:text-primary transition-colors">About</a>
              <a href="mailto:blinkbot07@gmail.com" className="hover:text-primary transition-colors">Support</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

// ─── Pricing Card Sub-Component ───────────────────────────────────────────────
function PricingCard({ title, priceInr, priceUsd, desc, features, isPopular }) {
  return (
    <div className={`relative bg-card border rounded-[28px] p-8 flex flex-col transition-all hover:-translate-y-1 hover:shadow-xl ${
      isPopular
        ? 'border-primary shadow-lg ring-1 ring-primary/20'
        : 'border-border'
    }`}>
      {isPopular && (
        <div className="absolute -top-3.5 left-1/2 -translate-x-1/2">
          <span className="bg-primary text-white text-[10px] font-extrabold px-4 py-1 rounded-full uppercase tracking-wider shadow-sm">
            Most Popular
          </span>
        </div>
      )}

      <div>
        <h3 className="text-2xl font-bold text-foreground">{title}</h3>
        <p className="text-sm text-muted-foreground mt-1.5 min-h-[44px] leading-relaxed">{desc}</p>

        <div className="mt-6 mb-7 flex items-baseline gap-2">
          <span className="text-5xl font-black tracking-tight text-foreground">
            {priceInr === "0" ? "Free" : `₹${priceInr}`}
          </span>
          {priceInr !== "0" && (
            <>
              <span className="text-muted-foreground font-medium">/mo</span>
              <span className="text-xs text-muted-foreground/60 font-mono">(${priceUsd})</span>
            </>
          )}
        </div>
      </div>

      <ul className="space-y-3.5 flex-1 mb-8 border-t border-border pt-6">
        {features.map((f, i) => (
          <li key={i} className="flex items-center gap-3 text-sm text-foreground">
            <Check size={15} className="text-emerald-500 shrink-0" />
            {f}
          </li>
        ))}
      </ul>

      <a
        href="https://app.blinkbot.in/login"
        className={`w-full text-center py-3.5 rounded-xl font-bold text-sm transition-all ${
          isPopular
            ? 'btn-primary shadow-md hover:shadow-lg'
            : 'bg-muted/50 hover:bg-muted border border-border text-foreground'
        }`}
      >
        {priceInr === "0" ? "Get Started Free" : `Upgrade to ${title}`}
      </a>
    </div>
  );
}

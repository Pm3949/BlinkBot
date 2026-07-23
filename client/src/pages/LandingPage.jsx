import { useState, useEffect, useRef } from 'react';
import { usePageSeo } from '../hooks/usePageSeo';
import { Link } from 'react-router-dom';
import { 
  Bot, Zap, Database, Globe, ArrowRight, Cpu, Sun, Moon, 
  Sparkles, Users, Upload, Settings, Code, Brain, 
  ChevronRight, ChevronLeft, Check, Send, Loader2, Star,
  CheckCircle2, Play, FileText, ChevronDown, Copy, Eye, Terminal, 
  Lightbulb, MessagesSquare, Sliders, HelpCircle, Wrench, Layers
} from 'lucide-react';
import Logo from '../components/shared/Logo';
import { useUIStore } from "../store/useUIStore";
import { toast } from 'sonner';

const API_URL = import.meta.env.VITE_API_BASE_URL || '';

// Supported LLM Providers in Codebase
const LLM_PROVIDERS = [
  { name: "OpenRouter", badge: "DeepSeek R1, Llama 3.3, Qwen", desc: "Connect OpenRouter API key for DeepSeek & open models." },
  { name: "OpenAI", badge: "GPT-4o & GPT-4o-mini", desc: "Industry standard models for multi-turn conversational agents." },
  { name: "Groq", badge: "Ultra-Fast Llama-3", desc: "Low latency responses powered by Groq LPU inference." },
  { name: "HuggingFace (HF)", badge: "Embeddings & Inference", desc: "Open source embedding models and inference endpoints." },
  { name: "Anthropic", badge: "Claude 3.5 Sonnet", desc: "High precision analysis for research and document search." },
  { name: "Google Gemini", badge: "Gemini 2.0 Flash", desc: "Large context window processing for complex datasets." }
];

// Demo personas for interactive sandbox
const DEMO_PERSONAS = [
  {
    id: 'support',
    name: 'Customer Support Bot',
    badge: 'Support & FAQ',
    docsCount: '34 PDFs & Help Guides',
    avatarBg: 'bg-primary',
    questions: [
      "What is your refund policy?",
      "How do I integrate OpenRouter API keys?",
      "Can I customize my chat widget design?"
    ],
    responses: {
      "What is your refund policy?": {
        answer: "We offer a 30-day money-back guarantee on all paid plans. You can initiate a refund or modify your plan directly from Workspace Billing.",
        sources: ["Refund_Policy.pdf (p. 2)", "Terms_of_Service.md"]
      },
      "How do I integrate OpenRouter API keys?": {
        answer: "Go to Settings > Provider Credentials & Keys, enter your OpenRouter API key, and select DeepSeek R1, Llama 3.3, or Qwen models.",
        sources: ["Provider_Setup_Guide.pdf"]
      },
      "Can I customize my chat widget design?": {
        answer: "Yes! You can customize brand color, header title, screen position (Bottom Left / Right), avatar, and system prompts in the Widget Configurator.",
        sources: ["Widget_Customization.md"]
      }
    }
  },
  {
    id: 'sales',
    name: 'Sales & Lead Qualifier',
    badge: 'Lead Gen',
    docsCount: 'Product Catalog & Specs',
    avatarBg: 'bg-purple-600',
    questions: [
      "What plans are available?",
      "Can I connect OpenRouter or HuggingFace?",
      "How do message top-ups work?"
    ],
    responses: {
      "What plans are available?": {
        answer: "We offer Starter (Free $0), Pro (₹999/mo | $12/mo), and Business (₹3,999/mo | $49/mo). Annual billing saves 20%.",
        sources: ["Pricing_Schedule_2026.pdf"]
      },
      "Can I connect OpenRouter or HuggingFace?": {
        answer: "Yes! BlinkBot supports OpenRouter, HuggingFace (HF), OpenAI, Groq, Anthropic Claude, and Google Gemini.",
        sources: ["LLM_Providers_Spec.pdf"]
      },
      "How do message top-ups work?": {
        answer: "Message top-up credit packs never expire: +5,000 Messages for ₹299 ($4) or +20,000 Messages for ₹899 ($11).",
        sources: ["Credit_Topups_Guide.pdf"]
      }
    }
  },
  {
    id: 'docs',
    name: 'Security & Legal Assistant',
    badge: 'Compliance',
    docsCount: '120 Policy Documents',
    avatarBg: 'bg-emerald-600',
    questions: [
      "Is client data shared with LLM providers?",
      "Where are vector embeddings stored?",
      "How does workspace access control work?"
    ],
    responses: {
      "Is client data shared with LLM providers?": {
        answer: "No. Uploaded files and chat logs remain isolated in your workspace. Data is never used to re-train public LLMs.",
        sources: ["Security_Whitepaper.pdf (p. 4)"]
      },
      "Where are vector embeddings stored?": {
        answer: "Vector embeddings are stored with Row Level Security (RLS) in pgvector / Supabase, encrypted at rest.",
        sources: ["Data_Security_Architecture.pdf"]
      },
      "How does workspace access control work?": {
        answer: "Workspaces allow inviting team members with Admin or Member roles, isolating datasets, and managing API credentials.",
        sources: ["Workspace_RBAC_Guide.pdf"]
      }
    }
  }
];

export default function LandingPage() {
  usePageSeo();
  const darkMode = useUIStore((state) => state.darkMode);
  const toggleDarkMode = useUIStore((state) => state.toggleDarkMode);

  // Billing cycle state
  const [annualBilling, setAnnualBilling] = useState(false);

  // Form State
  const [demoForm, setDemoForm] = useState({ name: '', email: '', company: '', message: '' });
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Interactive Simulator State
  const [activePersona, setActivePersona] = useState(DEMO_PERSONAS[0]);
  const [simChatHistory, setSimChatHistory] = useState([]);
  const [isSimTyping, setIsSimTyping] = useState(false);

  // Widget Customizer State
  const [customWidgetColor, setCustomWidgetColor] = useState('#FF4D00');
  const [customWidgetTitle, setCustomWidgetTitle] = useState('BlinkBot Assistant');
  const [customWidgetPosition, setCustomWidgetPosition] = useState('right');
  const [copiedSnippet, setCopiedSnippet] = useState(false);

  // Carousel Scroll Ref & FAQ State
  const featureScrollRef = useRef(null);
  const [openFaq, setOpenFaq] = useState(0);

  // Initialize Simulator Chat when Persona Changes
  useEffect(() => {
    const defaultQ = activePersona.questions[0];
    const defaultR = activePersona.responses[defaultQ];
    setSimChatHistory([
      { role: 'bot', text: `Hello! I am your **${activePersona.name}**. Ask me any question based on your uploaded documents!` },
      { role: 'user', text: defaultQ },
      { role: 'bot', text: defaultR.answer, sources: defaultR.sources }
    ]);
  }, [activePersona]);

  const handleQuestionClick = (questionText) => {
    if (isSimTyping) return;
    
    const updatedHistory = [...simChatHistory, { role: 'user', text: questionText }];
    setSimChatHistory(updatedHistory);
    setIsSimTyping(true);

    setTimeout(() => {
      const response = activePersona.responses[questionText] || {
        answer: "I searched your document vector index and retrieved relevant context to answer your request.",
        sources: ["Document_Index.pdf"]
      };
      setSimChatHistory([...updatedHistory, { role: 'bot', text: response.answer, sources: response.sources }]);
      setIsSimTyping(false);
    }, 600);
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
      if (!res.ok) throw new Error('Submission failed');
      toast.success("Demo request submitted! We will reach out shortly.");
      setDemoForm({ name: '', email: '', company: '', message: '' });
    } catch {
      toast.error("Could not submit request right now. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const copyWidgetScript = () => {
    const scriptTag = `<script 
  src="https://blinkbot.in/widget.js" 
  data-chatbot-id="bot_demo_9823"
  data-color="${customWidgetColor}"
  data-position="${customWidgetPosition}"
  async>
</script>`;
    navigator.clipboard.writeText(scriptTag);
    setCopiedSnippet(true);
    toast.success("Script snippet copied!");
    setTimeout(() => setCopiedSnippet(false), 2000);
  };

  const scrollFeatures = (direction) => {
    if (featureScrollRef.current) {
      const scrollAmount = direction === 'left' ? -350 : 350;
      featureScrollRef.current.scrollBy({ left: scrollAmount, behavior: 'smooth' });
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground font-sans selection:bg-primary/20 overflow-x-hidden transition-colors duration-300">
      
      {/* ═══════════════════════ NAVIGATION ═══════════════════════ */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-background/90 backdrop-blur-xl border-b border-border/80 transition-colors">
        <div className="flex items-center justify-between px-6 md:px-10 py-4 max-w-7xl mx-auto">
          <Logo />
          
          <div className="hidden md:flex items-center gap-8">
            <a href="#features-carousel" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">Features</a>
            <a href="#sandbox" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">Live Sandbox</a>
            <a href="#providers" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">LLM Providers</a>
            <a href="#widget-customizer" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">Widget Configurator</a>
            <a href="#pricing-slider" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">Pricing</a>
            <a href="#faq" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">FAQ</a>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={toggleDarkMode}
              type="button"
              aria-label="Toggle theme"
              className="h-10 w-10 rounded-xl border border-border text-muted-foreground flex items-center justify-center hover:bg-muted hover:text-foreground transition-all shadow-xs"
            >
              {darkMode ? <Sun size={18} className="text-amber-400" /> : <Moon size={18} />}
            </button>
            
            <Link to="/login" className="text-sm font-semibold hover:text-primary transition-colors hidden sm:inline px-3 py-2">
              Log in
            </Link>
            
            <Link to="/login" className="btn-primary px-5 py-2.5 rounded-full text-sm font-bold shadow-md hover:shadow-lg hover:scale-[1.02] transition-all flex items-center gap-1.5">
              <Zap size={15} /> Get Started Free
            </Link>
          </div>
        </div>
      </nav>

      {/* ═══════════════════════ HERO SECTION ═══════════════════════ */}
      <section className="relative pt-36 md:pt-44 pb-20 md:pb-28 flex flex-col items-center text-center px-6">
        <div className="inline-flex items-center gap-2.5 px-4 py-2 rounded-full border border-primary/30 bg-primary/10 text-primary text-xs sm:text-sm font-semibold mb-8">
          <Brain size={16} />
          <span>Meta-Agent Assisted RAG Platform</span>
          <span className="h-1.5 w-1.5 rounded-full bg-primary" />
          <span className="text-xs opacity-90">OpenRouter & HF Supported</span>
        </div>

        <h1 className="text-4xl sm:text-6xl md:text-7xl font-black tracking-tight max-w-5xl leading-[1.15] text-foreground">
          Build & Deploy AI Chatbots <br className="hidden sm:inline" />
          <span className="text-primary">
            Trained on Your Documents
          </span>
        </h1>

        <p className="mt-6 text-lg sm:text-xl text-muted-foreground max-w-3xl leading-relaxed">
          Upload PDFs, CSVs, or web links. Power your agents with OpenRouter (DeepSeek R1, Llama 3.3, Qwen), OpenAI, Groq, or HuggingFace (HF), and embed a lightweight chat widget in minutes.
        </p>

        <div className="mt-10 flex flex-col sm:flex-row items-center gap-4">
          <Link to="/login" className="w-full sm:w-auto btn-primary px-8 py-4 rounded-full text-base font-bold shadow-lg hover:shadow-xl hover:scale-[1.03] transition-all flex items-center justify-center gap-2">
            Start Building Free <ArrowRight size={18} />
          </Link>
          <a href="#sandbox" className="w-full sm:w-auto px-8 py-4 rounded-full text-base font-semibold border border-border bg-card hover:bg-muted transition-all flex items-center justify-center gap-2 shadow-xs">
            <Play size={16} className="text-primary fill-primary" /> Test Sandbox Simulator
          </a>
        </div>

        <div className="mt-12 flex flex-wrap items-center justify-center gap-6 sm:gap-10 text-xs text-muted-foreground font-medium">
          <div className="flex items-center gap-2"><CheckCircle2 size={16} className="text-emerald-500" /> Free Starter Tier Included</div>
          <div className="flex items-center gap-2"><CheckCircle2 size={16} className="text-emerald-500" /> OpenRouter & HF Keys Supported</div>
          <div className="flex items-center gap-2"><CheckCircle2 size={16} className="text-emerald-500" /> 1-Click HTML Script Embed</div>
        </div>
      </section>

      {/* ═══════════════════════ SUPPORTED PROVIDERS STRIP ═══════════════════════ */}
      <section id="providers" className="py-12 border-y border-border bg-card">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-8">
            <div className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Supported LLM Providers & Embedding Engines
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            {LLM_PROVIDERS.map((provider, i) => (
              <div 
                key={i} 
                className="p-4 rounded-2xl bg-background border border-border text-center transition-all hover:-translate-y-1 shadow-xs hover:border-primary/40"
              >
                <div className="font-bold text-sm text-foreground mb-1">{provider.name}</div>
                <div className="text-[11px] font-semibold text-primary mb-1.5">{provider.badge}</div>
                <div className="text-[10px] text-muted-foreground leading-tight">{provider.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════════════════════ SLIDING FEATURE CARDS CAROUSEL ═══════════════════════ */}
      <section id="features-carousel" className="py-20 md:py-28 px-6 max-w-7xl mx-auto">
        <div className="flex flex-col md:flex-row items-start md:items-end justify-between mb-12 gap-4">
          <div>
            <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-primary/10 text-primary text-xs font-bold uppercase tracking-wider mb-3">
              <Layers size={14} /> Sliding Feature Cards
            </div>
            <h2 className="text-3xl md:text-5xl font-extrabold tracking-tight text-foreground">
              Platform Features at a Glance
            </h2>
          </div>

          {/* Carousel Arrows */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => scrollFeatures('left')}
              className="h-11 w-11 rounded-2xl bg-card border border-border flex items-center justify-center text-foreground hover:bg-primary hover:text-white hover:border-primary transition-all shadow-xs"
              aria-label="Previous slide"
            >
              <ChevronLeft size={20} />
            </button>
            <button
              onClick={() => scrollFeatures('right')}
              className="h-11 w-11 rounded-2xl bg-card border border-border flex items-center justify-center text-foreground hover:bg-primary hover:text-white hover:border-primary transition-all shadow-xs"
              aria-label="Next slide"
            >
              <ChevronRight size={20} />
            </button>
          </div>
        </div>

        {/* Scrollable Container */}
        <div 
          ref={featureScrollRef}
          className="flex gap-6 overflow-x-auto scrollbar-none snap-x snap-mandatory py-4 px-1"
          style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
        >
          <SlidingFeatureCard 
            icon={Brain} 
            title="Meta-Agent Prompting" 
            badge="AI Assisted"
            desc="Provide your bot objective. Meta-Agent automatically generates structured system prompts, persona settings, and response rules."
          />
          <SlidingFeatureCard 
            icon={Database} 
            title="Multi-Format Vector RAG" 
            badge="PDF, CSV, TXT & Web"
            desc="Ingest PDF manuals, CSV datasets, text files, or crawl website URLs. Auto-chunks text into pgvector / Supabase embeddings."
          />
          <SlidingFeatureCard 
            icon={Cpu} 
            title="OpenRouter & HF Integration" 
            badge="Open Models"
            desc="Plug in OpenRouter API keys to access DeepSeek R1, Llama 3.3, and Qwen 2.5 Coder, or use HuggingFace (HF) models."
          />
          <SlidingFeatureCard 
            icon={Globe} 
            title="1-Line Script Widget" 
            badge="No Code Embed"
            desc="Embed responsive chat widgets on HTML, React, WordPress, or Shopify sites with a single customizable script tag."
          />
          <SlidingFeatureCard 
            icon={Wrench} 
            title="Memory Patching & Tracing" 
            badge="Self-Learning"
            desc="Inspect real-time trace logs, flag incorrect responses, and apply Memory Patches to auto-correct bot behavior instantly."
          />
          <SlidingFeatureCard 
            icon={Users} 
            title="Isolated Workspaces & RBAC" 
            badge="Team Collaboration"
            desc="Create team workspaces, assign Admin/Member roles, isolate datasets, and manage encrypted API key credentials."
          />
        </div>
      </section>

      {/* ═══════════════════════ INTERACTIVE SANDBOX ═══════════════════════ */}
      <section id="sandbox" className="py-20 md:py-28 bg-card border-y border-border px-6">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-12">
            <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-primary/10 text-primary text-xs font-bold uppercase tracking-wider mb-4">
              <Terminal size={14} /> Interactive Live Sandbox
            </div>
            <h2 className="text-3xl md:text-5xl font-extrabold tracking-tight text-foreground">
              Try Grounded RAG Retrieval Live
            </h2>
            <p className="mt-4 text-muted-foreground text-base max-w-2xl mx-auto">
              Select a persona card below to query documents and view real-time citation source tags.
            </p>
          </div>

          {/* Persona Card Carousel */}
          <div className="flex flex-wrap items-center justify-center gap-4 mb-8">
            {DEMO_PERSONAS.map((persona) => (
              <button
                key={persona.id}
                onClick={() => setActivePersona(persona)}
                className={`flex items-center gap-3 px-6 py-3.5 rounded-2xl text-sm font-bold transition-all ${
                  activePersona.id === persona.id
                    ? 'bg-primary text-white shadow-md scale-105'
                    : 'bg-background border border-border text-muted-foreground hover:text-foreground hover:border-primary/40'
                }`}
              >
                <div className={`w-3 h-3 rounded-full ${activePersona.id === persona.id ? 'bg-white' : 'bg-primary'}`} />
                {persona.name}
              </button>
            ))}
          </div>

          {/* Simulator Box */}
          <div className="max-w-4xl mx-auto bg-background border border-border rounded-[28px] shadow-xl overflow-hidden">
            {/* Header */}
            <div className="px-6 py-4 border-b border-border bg-muted/30 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`w-9 h-9 rounded-xl ${activePersona.avatarBg} flex items-center justify-center shadow-xs`}>
                  <Bot size={20} className="text-white" />
                </div>
                <div>
                  <div className="font-bold text-sm flex items-center gap-2 text-foreground">
                    {activePersona.name}
                    <span className="text-[11px] bg-primary/10 text-primary font-semibold px-2 py-0.5 rounded-full">
                      {activePersona.badge}
                    </span>
                  </div>
                  <div className="text-xs text-muted-foreground">{activePersona.docsCount}</div>
                </div>
              </div>
              
              <div className="flex items-center gap-2 text-xs font-semibold text-emerald-500 bg-emerald-500/10 px-3 py-1.5 rounded-full border border-emerald-500/20">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
                Context Active
              </div>
            </div>

            {/* Chat Messages */}
            <div className="p-6 md:p-8 space-y-4 min-h-[320px] max-h-[420px] overflow-y-auto bg-card text-xs">
              {simChatHistory.map((msg, idx) => (
                <div
                  key={idx}
                  className={`flex gap-3 items-start ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
                >
                  <div className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 text-xs font-bold ${
                    msg.role === 'user' ? 'bg-blue-600 text-white' : `${activePersona.avatarBg} text-white`
                  }`}>
                    {msg.role === 'user' ? 'You' : <Bot size={16} />}
                  </div>

                  <div className={`p-4 rounded-2xl max-w-[85%] text-sm leading-relaxed ${
                    msg.role === 'user'
                      ? 'bg-blue-600/10 border border-blue-500/20 text-foreground rounded-tr-xs'
                      : 'bg-background border border-border text-foreground shadow-xs rounded-tl-xs'
                  }`}>
                    <p>{msg.text}</p>
                    
                    {msg.sources && msg.sources.length > 0 && (
                      <div className="mt-3 pt-2.5 border-t border-border flex flex-wrap gap-1.5 items-center">
                        <span className="text-[11px] font-semibold text-muted-foreground flex items-center gap-1">
                          <FileText size={12} className="text-primary" /> Citation Sources:
                        </span>
                        {msg.sources.map((src, sIdx) => (
                          <span key={sIdx} className="text-[10px] font-medium bg-primary/10 text-primary px-2.5 py-0.5 rounded-md border border-primary/20">
                            {src}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {isSimTyping && (
                <div className="flex gap-3 items-center text-xs text-muted-foreground bg-muted/40 p-3 rounded-2xl max-w-xs">
                  <Loader2 size={16} className="animate-spin text-primary" />
                  Querying vector embeddings...
                </div>
              )}
            </div>

            {/* Prompt Buttons */}
            <div className="p-4 border-t border-border bg-muted/30">
              <div className="text-xs font-semibold text-muted-foreground mb-2 flex items-center gap-1.5">
                <Lightbulb size={14} className="text-amber-500" /> Click a sample query:
              </div>
              <div className="flex flex-wrap gap-2">
                {activePersona.questions.map((q, qIdx) => (
                  <button
                    key={qIdx}
                    onClick={() => handleQuestionClick(q)}
                    disabled={isSimTyping}
                    className="text-xs bg-card hover:bg-muted border border-border text-foreground px-3.5 py-2 rounded-xl transition-all text-left flex items-center gap-1.5 shadow-xs"
                  >
                    <span>"{q}"</span>
                    <ChevronRight size={13} className="text-muted-foreground" />
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════════════════ WIDGET CONFIGURATOR ═══════════════════════ */}
      <section id="widget-customizer" className="py-20 md:py-28 px-6 max-w-7xl mx-auto">
        <div className="text-center mb-14">
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-amber-500/10 text-amber-600 dark:text-amber-400 text-xs font-bold uppercase tracking-wider mb-4">
            <Sliders size={14} /> Widget Configurator
          </div>
          <h2 className="text-3xl md:text-5xl font-extrabold tracking-tight text-foreground">
            Custom Widget Theme & Live Snippet
          </h2>
          <p className="mt-4 text-muted-foreground text-base max-w-2xl mx-auto">
            Customize accent color, header title, and screen position with instant script generation.
          </p>
        </div>

        <div className="grid lg:grid-cols-12 gap-8 items-center">
          {/* Controls */}
          <div className="lg:col-span-5 bg-card border border-border rounded-[24px] p-6 md:p-8 shadow-lg space-y-6">
            <div>
              <label className="text-sm font-semibold block mb-2 text-foreground">Header Title</label>
              <input
                type="text"
                value={customWidgetTitle}
                onChange={(e) => setCustomWidgetTitle(e.target.value)}
                className="w-full border border-border bg-background rounded-xl px-4 py-2.5 text-sm outline-none focus:ring-2 focus:ring-primary/30 text-foreground"
              />
            </div>

            <div>
              <label className="text-sm font-semibold block mb-2 text-foreground">Brand Accent Color</label>
              <div className="flex items-center gap-3">
                {['#FF4D00', '#2563EB', '#10B981', '#7C3AED', '#EC4899', '#F59E0B'].map((color) => (
                  <button
                    key={color}
                    onClick={() => setCustomWidgetColor(color)}
                    style={{ backgroundColor: color }}
                    className={`w-8 h-8 rounded-full border-2 transition-transform ${
                      customWidgetColor === color ? 'scale-125 border-foreground' : 'border-transparent hover:scale-110'
                    }`}
                  />
                ))}
                <input
                  type="color"
                  value={customWidgetColor}
                  onChange={(e) => setCustomWidgetColor(e.target.value)}
                  className="w-9 h-9 rounded-lg border border-border cursor-pointer bg-transparent"
                />
              </div>
            </div>

            <div>
              <label className="text-sm font-semibold block mb-2 text-foreground">Screen Position</label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  onClick={() => setCustomWidgetPosition('right')}
                  className={`py-2.5 px-4 rounded-xl text-xs font-semibold border transition-all ${
                    customWidgetPosition === 'right' ? 'bg-primary text-white border-primary' : 'bg-background border-border hover:bg-muted text-foreground'
                  }`}
                >
                  Bottom Right
                </button>
                <button
                  onClick={() => setCustomWidgetPosition('left')}
                  className={`py-2.5 px-4 rounded-xl text-xs font-semibold border transition-all ${
                    customWidgetPosition === 'left' ? 'bg-primary text-white border-primary' : 'bg-background border-border hover:bg-muted text-foreground'
                  }`}
                >
                  Bottom Left
                </button>
              </div>
            </div>

            {/* Script Snippet */}
            <div className="pt-2">
              <div className="flex items-center justify-between text-xs font-semibold mb-2">
                <span className="text-muted-foreground flex items-center gap-1"><Code size={13} /> HTML Snippet</span>
                <button
                  onClick={copyWidgetScript}
                  className="text-primary hover:underline flex items-center gap-1 font-bold"
                >
                  {copiedSnippet ? <Check size={13} /> : <Copy size={13} />}
                  {copiedSnippet ? 'Copied!' : 'Copy Code'}
                </button>
              </div>
              <div className="bg-slate-950 text-slate-200 p-4 rounded-xl text-xs font-mono overflow-x-auto leading-relaxed border border-slate-800">
                <code>{`<script src="https://blinkbot.in/widget.js"`}<br />
                {`  data-chatbot-id="bot_demo_9823"`}<br />
                {`  data-color="${customWidgetColor}"`}<br />
                {`  data-position="${customWidgetPosition}" async>`}<br />
                {`</script>`}</code>
              </div>
            </div>
          </div>

          {/* Live Mock Window */}
          <div className="lg:col-span-7 flex flex-col items-center justify-center relative min-h-[420px] bg-card border border-border rounded-[28px] p-6 shadow-xl">
            <div className="text-xs text-muted-foreground font-semibold mb-4 flex items-center gap-1.5">
              <Eye size={14} className="text-primary" /> Live Widget Preview
            </div>

            <div className="w-full max-w-sm bg-background border border-border rounded-2xl shadow-xl overflow-hidden transition-all duration-300">
              <div style={{ backgroundColor: customWidgetColor }} className="p-4 text-white flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center">
                    <Bot size={18} className="text-white" />
                  </div>
                  <div>
                    <div className="font-bold text-sm">{customWidgetTitle || 'BlinkBot'}</div>
                    <div className="text-[11px] opacity-90">Online | Powered by BlinkBot</div>
                  </div>
                </div>
              </div>

              <div className="p-4 space-y-3 bg-card text-xs min-h-[220px]">
                <div className="bg-background border border-border p-3 rounded-xl max-w-[85%] text-foreground">
                  Hello! How can I assist you with your knowledge base today?
                </div>
                <div className="bg-primary/10 border border-primary/20 p-3 rounded-xl max-w-[85%] ml-auto text-right text-foreground">
                  Which LLM providers are supported?
                </div>
                <div className="bg-background border border-border p-3 rounded-xl max-w-[85%] text-foreground">
                  We support OpenRouter (DeepSeek R1/V3, Llama 3.3, Qwen), OpenAI, Groq, Anthropic Claude, Google Gemini, and HuggingFace!
                </div>
              </div>

              <div className="p-3 border-t border-border bg-background flex items-center gap-2">
                <div className="flex-1 bg-muted/40 rounded-xl px-3 py-2 text-xs text-muted-foreground">Type a message...</div>
                <button style={{ backgroundColor: customWidgetColor }} className="w-8 h-8 rounded-xl flex items-center justify-center text-white shrink-0">
                  <Send size={14} />
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════════════════ SLIDING PRICING CARDS ═══════════════════════ */}
      <section id="pricing-slider" className="py-20 md:py-28 bg-card border-y border-border px-6">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-12">
            <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-amber-500/10 text-amber-600 dark:text-amber-400 text-xs font-bold uppercase tracking-wider mb-4">
              <Star size={14} /> Workspace Plans
            </div>
            <h2 className="text-3xl md:text-5xl font-extrabold tracking-tight text-foreground">
              Transparent Workspace Pricing
            </h2>
            <p className="mt-4 text-muted-foreground text-base max-w-xl mx-auto">
              Start free. Upgrade as your team, agents, and message volume scale.
            </p>

            {/* Billing Cycle Toggle */}
            <div className="flex items-center justify-center gap-3 mt-8">
              <span className={`text-sm font-semibold ${!annualBilling ? 'text-foreground' : 'text-muted-foreground'}`}>Monthly</span>
              <button
                type="button"
                onClick={() => setAnnualBilling(!annualBilling)}
                className={`w-12 h-6 rounded-full transition-colors relative flex items-center p-0.5 ${
                  annualBilling ? 'bg-primary' : 'bg-muted'
                }`}
              >
                <span className={`w-5 h-5 rounded-full bg-white transition-transform ${
                  annualBilling ? 'translate-x-6' : 'translate-x-0'
                }`} />
              </button>
              <span className={`text-sm font-semibold flex items-center gap-1.5 ${annualBilling ? 'text-foreground' : 'text-muted-foreground'}`}>
                Annual Billing <span className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 text-xs font-bold px-2.5 py-0.5 rounded-full border border-emerald-500/20">Save 20%</span>
              </span>
            </div>
          </div>

          {/* Pricing Grid */}
          <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
            <PricingCard 
              title="Starter" 
              priceInr="0"
              priceUsd="0"
              desc="Free tier included for building your first agent."
              features={[
                "1 Active Workspace",
                "1 AI Agent per Workspace",
                "1,000 AI Messages / month",
                "100 MB Document Storage",
                "1 Public Website Chatbot",
                "Community Support"
              ]} 
            />
            <PricingCard 
              title="Pro" 
              priceInr={annualBilling ? "799" : "999"}
              priceUsd={annualBilling ? "10" : "12"}
              desc="Ideal for active projects, creators, and growing teams."
              features={[
                "3 Active Workspaces",
                "5 AI Agents per Workspace",
                "10,000 AI Messages / month",
                "1 GB Vector Storage",
                "3 Public Website Chatbots",
                "Granular Model & Provider Permissions",
                "Priority Support"
              ]} 
              isPopular 
            />
            <PricingCard 
              title="Business" 
              priceInr={annualBilling ? "3,199" : "3,999"}
              priceUsd={annualBilling ? "39" : "49"}
              desc="For scaling applications & agency deployments."
              features={[
                "Unlimited Workspaces",
                "20 AI Agents per Workspace",
                "50,000 AI Messages / month",
                "10 GB Vector Storage",
                "Unlimited Public Chatbots",
                "Full Audit Logging & RBAC Controls",
                "Dedicated Support Manager"
              ]} 
            />
          </div>

          {/* Message Topup Packs */}
          <div className="mt-12 max-w-4xl mx-auto bg-background border border-border rounded-2xl p-6 sm:p-8 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6 shadow-md">
            <div>
              <div className="font-bold text-base text-foreground flex items-center gap-2">
                <Zap size={18} className="text-amber-500 fill-amber-500" /> Non-Expiring Message Credit Top-Ups
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                Need extra capacity? Add +5,000 Messages (₹299 | $4) or +20,000 Messages (₹899 | $11) anytime.
              </p>
            </div>
            <Link to="/login" className="px-5 py-2.5 rounded-xl btn-primary text-xs font-bold shrink-0 shadow-md">
              Workspace Billing
            </Link>
          </div>
        </div>
      </section>

      {/* ═══════════════════════ FAQ SECTION ═══════════════════════ */}
      <section id="faq" className="py-20 md:py-28 px-6 max-w-4xl mx-auto">
        <div className="text-center mb-14">
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-blue-500/10 text-blue-600 dark:text-blue-400 text-xs font-bold uppercase tracking-wider mb-4">
            <HelpCircle size={14} /> FAQ
          </div>
          <h2 className="text-3xl md:text-5xl font-extrabold tracking-tight text-foreground">
            Frequently Asked Questions
          </h2>
        </div>

        <div className="space-y-4">
          {FAQS.map((faq, idx) => (
            <div 
              key={idx}
              className="bg-card border border-border rounded-2xl overflow-hidden transition-all shadow-xs"
            >
              <button
                onClick={() => setOpenFaq(openFaq === idx ? null : idx)}
                className="w-full px-6 py-5 text-left font-bold text-base flex items-center justify-between gap-4 text-foreground hover:text-primary transition-colors"
              >
                <span>{faq.q}</span>
                <ChevronDown size={18} className={`transition-transform duration-200 text-muted-foreground ${openFaq === idx ? 'rotate-180 text-primary' : ''}`} />
              </button>

              {openFaq === idx && (
                <div className="px-6 pb-6 text-sm text-muted-foreground leading-relaxed border-t border-border pt-4 bg-background/50">
                  {faq.a}
                </div>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* ═══════════════════════ BOOK A DEMO FORM ═══════════════════════ */}
      <section id="demo" className="py-20 md:py-28 px-6 max-w-4xl mx-auto">
        <div className="text-center mb-12">
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-primary/10 text-primary text-xs font-bold uppercase tracking-wider mb-4">
            <MessagesSquare size={14} /> Contact Us
          </div>
          <h2 className="text-3xl md:text-5xl font-extrabold tracking-tight text-foreground">
            Schedule a Demo & Walkthrough
          </h2>
          <p className="mt-4 text-muted-foreground text-base">
            Have high volume requirements or custom integration needs? Talk with our team.
          </p>
        </div>

        <form onSubmit={handleDemoSubmit} className="bg-card border border-border rounded-[28px] p-6 md:p-10 shadow-xl space-y-6">
          <div className="grid sm:grid-cols-2 gap-6">
            <div>
              <label className="text-sm font-semibold block mb-2 text-foreground">Full Name <span className="text-red-500">*</span></label>
              <input
                type="text"
                value={demoForm.name}
                onChange={(e) => setDemoForm({...demoForm, name: e.target.value})}
                className="w-full border border-border bg-background rounded-xl px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-primary/30 text-foreground"
                placeholder="Name"
                required
              />
            </div>
            <div>
              <label className="text-sm font-semibold block mb-2 text-foreground">Work Email <span className="text-red-500">*</span></label>
              <input
                type="email"
                value={demoForm.email}
                onChange={(e) => setDemoForm({...demoForm, email: e.target.value})}
                className="w-full border border-border bg-background rounded-xl px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-primary/30 text-foreground"
                placeholder="work@company.com"
                required
              />
            </div>
          </div>

          <div>
            <label className="text-sm font-semibold block mb-2 text-foreground">Company</label>
            <input
              type="text"
              value={demoForm.company}
              onChange={(e) => setDemoForm({...demoForm, company: e.target.value})}
              className="w-full border border-border bg-background rounded-xl px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-primary/30 text-foreground"
              placeholder="Acme Corp"
            />
          </div>

          <div>
            <label className="text-sm font-semibold block mb-2 text-foreground">Requirements / Message</label>
            <textarea
              rows={4}
              value={demoForm.message}
              onChange={(e) => setDemoForm({...demoForm, message: e.target.value})}
              className="w-full border border-border bg-background rounded-xl px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-primary/30 resize-y text-foreground"
              placeholder="Tell us about your documents or custom integration requirements..."
            />
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full btn-primary py-4 rounded-xl text-base font-bold shadow-lg hover:shadow-xl flex items-center justify-center gap-2 transition-all disabled:opacity-75"
          >
            {isSubmitting ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
            {isSubmitting ? "Submitting..." : "Send Request"}
          </button>
        </form>
      </section>

      {/* ═══════════════════════ FOOTER ═══════════════════════ */}
      <footer className="border-t border-border bg-card">
        <div className="max-w-7xl mx-auto px-6 md:px-8 py-16">
          <div className="grid md:grid-cols-4 gap-10 md:gap-16">
            <div className="md:col-span-1 space-y-4">
              <Logo />
              <p className="text-sm text-muted-foreground leading-relaxed">
                Build, train, and embed custom RAG AI bots with your knowledge base.
              </p>
            </div>

            <div>
              <h4 className="font-bold text-sm uppercase tracking-wider mb-4 text-foreground">Platform</h4>
              <ul className="space-y-3 text-sm text-muted-foreground">
                <li><a href="#features-carousel" className="hover:text-primary transition-colors">Features</a></li>
                <li><a href="#sandbox" className="hover:text-primary transition-colors">Live Sandbox</a></li>
                <li><a href="#widget-customizer" className="hover:text-primary transition-colors">Widget Generator</a></li>
                <li><a href="#pricing-slider" className="hover:text-primary transition-colors">Pricing</a></li>
              </ul>
            </div>

            <div>
              <h4 className="font-bold text-sm uppercase tracking-wider mb-4 text-foreground">Resources</h4>
              <ul className="space-y-3 text-sm text-muted-foreground">
                <li><Link to="/user-guide" className="hover:text-primary transition-colors">User Documentation</Link></li>
                <li><Link to="/blog" className="hover:text-primary transition-colors">Product Blog</Link></li>
                <li><Link to="/login" className="hover:text-primary transition-colors">Studio Console</Link></li>
              </ul>
            </div>

            <div>
              <h4 className="font-bold text-sm uppercase tracking-wider mb-4 text-foreground">Company</h4>
              <ul className="space-y-3 text-sm text-muted-foreground">
                <li><Link to="/about" className="hover:text-primary transition-colors">About Us</Link></li>
                <li><Link to="/terms" className="hover:text-primary transition-colors">Terms of Service</Link></li>
                <li><a href="mailto:techmate.ed@gmail.com" className="hover:text-primary transition-colors">Contact Support</a></li>
              </ul>
            </div>
          </div>

          <div className="border-t border-border mt-12 pt-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-muted-foreground">
            <p>© {new Date().getFullYear()} BlinkBot. All rights reserved.</p>
            <div className="flex items-center gap-6 font-medium">
              <Link to="/terms" className="hover:text-primary transition-colors">Privacy & Terms</Link>
              <Link to="/about" className="hover:text-primary transition-colors">About</Link>
              <a href="mailto:techmate.ed@gmail.com" className="hover:text-primary transition-colors">Support</a>
            </div>
          </div>
        </div>
      </footer>

    </div>
  );
}

/* ═══════════════════════ SUB-COMPONENTS ═══════════════════════ */

function SlidingFeatureCard({ icon: Icon, title, badge, desc }) {
  return (
    <div className="w-[300px] sm:w-[340px] shrink-0 snap-start bg-card border border-border rounded-[24px] p-7 hover:border-primary/50 hover:shadow-lg transition-all duration-300 flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between mb-5">
          <div className="w-12 h-12 rounded-2xl bg-primary/10 text-primary flex items-center justify-center">
            <Icon size={24} />
          </div>
          <span className="text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-full bg-muted text-muted-foreground border border-border">
            {badge}
          </span>
        </div>
        <h3 className="text-xl font-bold mb-2.5 text-foreground">{title}</h3>
        <p className="text-sm text-muted-foreground leading-relaxed">{desc}</p>
      </div>
    </div>
  );
}

function PricingCard({ title, priceInr, priceUsd, desc, features, isPopular }) {
  return (
    <div className={`relative bg-card border rounded-[28px] p-8 flex flex-col transition-all hover:-translate-y-1 hover:shadow-xl ${
      isPopular 
        ? 'border-primary shadow-lg ring-1 ring-primary/30' 
        : 'border-border'
    }`}>
      {isPopular && (
        <div className="absolute -top-3.5 left-1/2 -translate-x-1/2">
          <span className="bg-primary text-white text-[10px] font-extrabold px-3.5 py-1 rounded-full uppercase tracking-wider shadow-xs">
            Most Popular
          </span>
        </div>
      )}

      <h3 className="text-2xl font-bold text-foreground">{title}</h3>
      <p className="text-sm text-muted-foreground mt-1.5 min-h-[40px]">{desc}</p>

      <div className="mt-6 mb-6 flex items-baseline gap-2">
        <span className="text-5xl font-black tracking-tight text-foreground">₹{priceInr}</span>
        <span className="text-muted-foreground font-medium">/month</span>
        <span className="text-xs text-muted-foreground/60 font-mono">(${priceUsd})</span>
      </div>

      <ul className="space-y-3.5 flex-1 mb-8 border-t border-border pt-6">
        {features.map((f, i) => (
          <li key={i} className="flex items-center gap-3 text-sm text-foreground">
            <Check size={16} className="text-emerald-500 shrink-0 font-bold" />
            <span>{f}</span>
          </li>
        ))}
      </ul>

      <Link
        to="/login"
        className={`w-full text-center py-3.5 rounded-xl font-bold text-sm transition-all ${
          isPopular
            ? 'btn-primary shadow-md hover:shadow-lg'
            : 'bg-muted/50 hover:bg-muted border border-border text-foreground'
        }`}
      >
        {priceInr === "0" ? "Included Free" : `Upgrade to ${title}`}
      </Link>
    </div>
  );
}

const FAQS = [
  {
    q: "Which LLM model providers can I use with BlinkBot?",
    a: "BlinkBot supports OpenRouter (access DeepSeek R1, DeepSeek V3, Llama 3.3 70B, Qwen 2.5 Coder, Gemini 2.0 Flash), OpenAI (GPT-4o, GPT-4o-mini), Groq, Anthropic Claude 3.5 Sonnet, Google Gemini, and HuggingFace (HF) embeddings & models."
  },
  {
    q: "How do I connect OpenRouter or HuggingFace (HF) API keys?",
    a: "In your workspace, go to Settings > Provider Credentials & Keys, enter your encrypted API key, and select your preferred model from the dropdown."
  },
  {
    q: "Do I need coding experience to deploy a chat widget?",
    a: "No coding required! Simply upload your files or website links, configure your bot persona in the dashboard, and copy-paste a 1-line script tag into your website HTML."
  },
  {
    q: "Is my document data safe and kept private?",
    a: "Yes. All vector embeddings are encrypted at rest with AES-256 and protected with Row Level Security (RLS) in pgvector / Supabase. Your data is never shared or used to re-train public LLM models."
  },
  {
    q: "Can I buy additional message credits if I exceed my monthly plan?",
    a: "Yes! Non-expiring message credit top-up packs are available in your Billing settings: +5,000 Messages for ₹299 ($4) or +20,000 Messages for ₹899 ($11)."
  }
];

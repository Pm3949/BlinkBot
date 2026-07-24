import { useState, useEffect, useRef } from 'react';
import { usePageSeo } from '../hooks/usePageSeo';
import { Link } from 'react-router-dom';
import {
  Bot, Zap, Database, Globe, ArrowRight, Cpu, Sun, Moon,
  Sparkles, Users, Upload, Settings, Code, Brain,
  ChevronRight, ChevronLeft, Check, Send, Loader2, Star,
  CheckCircle2, Play, FileText, ChevronDown, Copy, Eye, Terminal,
  Lightbulb, MessagesSquare, Sliders, HelpCircle, Wrench, Layers,
  ShieldCheck, Clock, TrendingUp, Rocket, BookOpen, MessageSquare,
  AlertCircle, ArrowUpRight, BarChart3, Lock, Puzzle, Search
} from 'lucide-react';
import Logo from '../components/shared/Logo';
import { useUIStore } from "../store/useUIStore";
import { toast } from 'sonner';

const API_URL = import.meta.env.VITE_API_BASE_URL || '';

// ─── LLM Provider Data ──────────────────────────────────────────────────────
const LLM_PROVIDERS = [
  { name: "OpenRouter", badge: "Access to Everything", icon: "🔀", desc: "DeepSeek, Llama 3.3, Qwen & more." },
  { name: "OpenAI", badge: "GPT-4o & More", icon: "⚡", desc: "The industry benchmark for conversational AI." },
  { name: "Groq", badge: "Lightning Fast", icon: "🚀", desc: "Near-instant responses via hardware acceleration." },
  { name: "HuggingFace", badge: "Open Source", icon: "🤗", desc: "Plug in any open-source embedding model." },
  { name: "Anthropic", badge: "Claude Sonnet", icon: "🧠", desc: "Deep reasoning and careful long-form analysis." },
  { name: "Google Gemini", badge: "Gemini Flash", icon: "✨", desc: "Handles massive documents effortlessly." },
];

// ─── Demo Personas for Sandbox ───────────────────────────────────────────────
const DEMO_PERSONAS = [
  {
    id: 'support',
    name: 'Helpdesk Assistant',
    badge: 'Customer Support',
    docsCount: 'Trained on 12 Help Guides',
    avatarBg: 'bg-blue-500',
    emoji: '🎧',
    questions: [
      "What is your refund policy?",
      "How do I add my team members?",
      "Can I change the widget color?",
    ],
    responses: {
      "What is your refund policy?": {
        answer: "We offer a full 30-day money-back guarantee—no questions asked. You can cancel or switch your plan anytime from the Billing page in your workspace.",
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
    emoji: '💼',
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
        answer: "Yes! Connect your OpenRouter or HuggingFace API key to access hundreds of open-source models like DeepSeek R1, Llama 3.3, Mistral, and Qwen—at near-zero cost.",
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
    emoji: '📋',
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
        answer: "Core office hours are 9 AM to 5 PM, Monday through Friday. Most teams have flexible hours—coordinate with your manager. Remote-first teams should overlap at least 3 hours with the core window.",
        sources: ["Office_Policies.pdf"],
      },
    },
  },
];

// ─── FAQ Data ─────────────────────────────────────────────────────────────────
const FAQS = [
  {
    q: "Which AI models can I use?",
    a: "You can connect OpenRouter, OpenAI, Groq, Anthropic Claude, Google Gemini, and HuggingFace. Switch models any time without losing your data or settings—BlinkBot is completely model-agnostic.",
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
    a: "Purchase a non-expiring top-up pack from the Billing page at any time. Extra credits stack on top of your monthly allowance and roll over—they never reset.",
  },
  {
    q: "Can I invite my team to collaborate?",
    a: "Yes. Invite colleagues to your workspace and assign granular roles—Admin, Member, or Viewer. Admins can manage agents and data; Viewers can only read. Fine-grained permission toggles let you control exactly what each member can access.",
  },
];

// ─── How It Works Steps ───────────────────────────────────────────────────────
const HOW_IT_WORKS = [
  {
    step: "01",
    icon: Upload,
    title: "Upload Your Documents",
    desc: "Drop in PDFs, text files, or paste website URLs. BlinkBot parses, chunks, and vectorizes everything automatically—your knowledge base is ready in under 60 seconds.",
    accent: "from-blue-500/20 to-blue-500/5",
    iconColor: "text-blue-500",
    iconBg: "bg-blue-500/10",
  },
  {
    step: "02",
    icon: Cpu,
    title: "Configure Your AI",
    desc: "Choose your LLM provider, define a personality with a system prompt (or let AI generate one for you), and tune your embedding strategy. No PhD required.",
    accent: "from-purple-500/20 to-purple-500/5",
    iconColor: "text-purple-500",
    iconBg: "bg-purple-500/10",
  },
  {
    step: "03",
    icon: Globe,
    title: "Deploy in One Click",
    desc: "Copy the generated script tag and paste it into any website. Your branded AI assistant goes live instantly—no servers, no infrastructure headaches.",
    accent: "from-orange-500/20 to-orange-500/5",
    iconColor: "text-primary",
    iconBg: "bg-primary/10",
  },
];

// ─── Core Feature Cards ───────────────────────────────────────────────────────
const FEATURE_CARDS = [
  {
    icon: Brain,
    title: "Auto-Prompt Generation",
    badge: "AI Assisted",
    desc: "Describe what you want your bot to do in plain English. BlinkBot generates the perfect system prompt and rules for it automatically.",
    gradient: "from-violet-500/10 to-violet-500/0",
    borderHover: "hover:border-violet-500/40",
    iconBg: "bg-violet-500/10",
    iconColor: "text-violet-500",
  },
  {
    icon: Database,
    title: "Chat with Your Data",
    badge: "RAG Engine",
    desc: "Upload manuals, policies, or website links. The AI reads and understands them instantly to answer questions grounded in your content—not hallucinations.",
    gradient: "from-blue-500/10 to-blue-500/0",
    borderHover: "hover:border-blue-500/40",
    iconBg: "bg-blue-500/10",
    iconColor: "text-blue-500",
  },
  {
    icon: Cpu,
    title: "Bring Your Own AI",
    badge: "Model Choice",
    desc: "Prefer OpenAI, Claude, or open-source models? Plug in your API keys and switch between providers with a single click—no vendor lock-in.",
    gradient: "from-cyan-500/10 to-cyan-500/0",
    borderHover: "hover:border-cyan-500/40",
    iconBg: "bg-cyan-500/10",
    iconColor: "text-cyan-500",
  },
  {
    icon: Globe,
    title: "No-Code Website Widget",
    badge: "1-Line Embed",
    desc: "Paste one script tag into your site's HTML and your AI chat widget goes live. Works on WordPress, Shopify, React, and everything in between.",
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
    icon: Search,
    title: "Real-Time Web Search",
    badge: "Live Context",
    desc: "Toggle on the live web search integration to blend your private knowledge base with real-time internet context via DuckDuckGo—best of both worlds.",
    gradient: "from-amber-500/10 to-amber-500/0",
    borderHover: "hover:border-amber-500/40",
    iconBg: "bg-amber-500/10",
    iconColor: "text-amber-500",
  },
  {
    icon: ShieldCheck,
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
    desc: "Flag wrong answers directly in the chat interface and add your correction. The bot incorporates your feedback instantly—no model retraining needed.",
    gradient: "from-teal-500/10 to-teal-500/0",
    borderHover: "hover:border-teal-500/40",
    iconBg: "bg-teal-500/10",
    iconColor: "text-teal-500",
  },
];

// ─── Pain Points (Why BlinkBot) ───────────────────────────────────────────────
const PAIN_POINTS = [
  {
    pain: "Your team is drowning in repetitive support tickets that all have the same answers buried in a PDF.",
    solve: "BlinkBot reads that PDF and answers every question automatically, 24/7.",
    icon: AlertCircle,
  },
  {
    pain: "You've tried ChatGPT but it keeps making things up—hallucinations kill customer trust.",
    solve: "BlinkBot only answers from your documents. No guessing, always cited.",
    icon: AlertCircle,
  },
  {
    pain: "Setting up a custom AI chatbot requires a backend engineer, a DevOps team, and weeks of work.",
    solve: "BlinkBot gets you from zero to live AI assistant in under 10 minutes.",
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

// ─── Main Component ───────────────────────────────────────────────────────────
export default function LandingPage() {
  usePageSeo();
  const darkMode = useUIStore((state) => state.darkMode);
  const toggleDarkMode = useUIStore((state) => state.toggleDarkMode);

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

  // Feature scroll ref & FAQ state
  const featureScrollRef = useRef(null);
  const [openFaq, setOpenFaq] = useState(0);

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
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={toggleDarkMode}
              type="button"
              aria-label="Toggle theme"
              className="h-9 w-9 rounded-xl border border-border text-muted-foreground flex items-center justify-center hover:bg-muted hover:text-foreground transition-all"
            >
              {darkMode ? <Sun size={16} className="text-amber-400" /> : <Moon size={16} />}
            </button>

            <Link to="/login" className="text-sm font-semibold hover:text-primary transition-colors hidden sm:inline px-3 py-2">
              Log in
            </Link>

            <Link
              to="/login"
              className="btn-primary px-5 py-2.5 rounded-full text-sm font-bold shadow-md hover:shadow-lg hover:scale-[1.02] transition-all flex items-center gap-1.5"
            >
              <Zap size={14} /> Get Started Free
            </Link>
          </div>
        </div>
      </nav>

      {/* ═══════════════════════════════════════════════════════════════════
          HERO SECTION
      ═══════════════════════════════════════════════════════════════════ */}
      <section className="relative pt-36 md:pt-44 pb-24 md:pb-32 flex flex-col items-center text-center px-6 overflow-hidden">
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

        {/* Badge */}
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-primary/30 bg-primary/8 text-primary text-xs sm:text-sm font-semibold mb-8 shadow-sm">
          <Sparkles size={14} className="animate-pulse" />
          <span>Turn your documents into a 24/7 AI expert — in minutes</span>
        </div>

        {/* Headline */}
        <h1 className="text-4xl sm:text-6xl md:text-7xl font-extrabold tracking-tight max-w-5xl leading-[1.1] text-foreground">
          Your Knowledge Base.{' '}
          <br className="hidden sm:inline" />
          <span className="relative inline-block">
            <span
              className="bg-clip-text text-transparent"
              style={{ backgroundImage: 'linear-gradient(135deg, #FF4D00 0%, #FF8C00 100%)' }}
            >
              Your AI Assistant.
            </span>
          </span>
          <br className="hidden sm:inline" />
          <span className="text-foreground/70 font-medium text-3xl sm:text-4xl md:text-5xl mt-2 block">
            Zero Code. Full Control.
          </span>
        </h1>

        {/* Sub-headline */}
        <p className="mt-8 text-lg sm:text-xl text-muted-foreground max-w-2xl leading-relaxed">
          Upload your PDFs and docs. Pick your favorite AI model. Watch your private, citation-grounded assistant 
          answer every question — then embed it on your website in seconds.
        </p>
        {/* CTAs */}
        <div className="mt-10 flex flex-col sm:flex-row items-center gap-4">
          <Link
            to="/login"
            className="w-full sm:w-auto btn-primary px-8 py-4 rounded-full text-base font-bold shadow-lg hover:shadow-xl hover:scale-[1.03] transition-all flex items-center justify-center gap-2 group"
          >
            Start Building — It's Free
            <ArrowRight size={18} className="group-hover:translate-x-0.5 transition-transform" />
          </Link>
          <a
            href="#sandbox"
            className="w-full sm:w-auto px-8 py-4 rounded-full text-base font-semibold border border-border bg-card hover:bg-muted transition-all flex items-center justify-center gap-2 shadow-xs"
          >
            <Play size={15} className="text-primary fill-primary" /> See It Live
          </a>
        </div>

        {/* Trust badges */}
        <div className="mt-10 flex flex-wrap items-center justify-center gap-6 sm:gap-8 text-xs text-muted-foreground font-medium">
          <div className="flex items-center gap-1.5">
            <CheckCircle2 size={15} className="text-emerald-500" />
            Free Starter Plan Included
          </div>
          <div className="flex items-center gap-1.5">
            <CheckCircle2 size={15} className="text-emerald-500" />
            No credit card required
          </div>
          <div className="flex items-center gap-1.5">
            <CheckCircle2 size={15} className="text-emerald-500" />
            6 LLM providers supported
          </div>
          <div className="flex items-center gap-1.5">
            <CheckCircle2 size={15} className="text-emerald-500" />
            Embed in 1 line of HTML
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
            <Link
              to="/login"
              className="inline-flex items-center gap-2 btn-primary px-8 py-4 rounded-full text-base font-bold shadow-lg hover:shadow-xl hover:scale-[1.03] transition-all"
            >
              Try It Right Now — Free <ArrowRight size={18} />
            </Link>
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
              className="h-11 w-11 rounded-2xl bg-card border border-border flex items-center justify-center text-foreground hover:bg-primary hover:text-white hover:border-primary transition-all shadow-xs"
              aria-label="Previous"
            >
              <ChevronLeft size={20} />
            </button>
            <button
              onClick={() => scrollFeatures('right')}
              className="h-11 w-11 rounded-2xl bg-card border border-border flex items-center justify-center text-foreground hover:bg-primary hover:text-white hover:border-primary transition-all shadow-xs"
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
                <div className="text-2xl mb-2">{provider.icon}</div>
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
              Ask it anything.
              <br />
              Watch it cite its sources.
            </h2>
            <p className="mt-4 text-muted-foreground text-base max-w-2xl mx-auto">
              These are real demo bots trained on sample documents. Every answer includes transparent citation tags 
              showing exactly which document the AI pulled from.
            </p>
          </div>

          {/* Persona Switcher */}
          <div className="flex flex-wrap items-center justify-center gap-3 mb-8">
            {DEMO_PERSONAS.map((persona) => (
              <button
                key={persona.id}
                onClick={() => setActivePersona(persona)}
                className={`flex items-center gap-2.5 px-5 py-3 rounded-2xl text-sm font-bold transition-all ${
                  activePersona.id === persona.id
                    ? 'bg-primary text-white shadow-md scale-105'
                    : 'bg-card border border-border text-muted-foreground hover:text-foreground hover:border-primary/30'
                }`}
              >
                <span>{persona.emoji}</span>
                {persona.name}
              </button>
            ))}
          </div>

          {/* Simulator Box */}
          <div className="bg-background border border-border rounded-[28px] shadow-xl overflow-hidden">
            {/* Header */}
            <div className="px-6 py-4 border-b border-border bg-muted/30 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`w-10 h-10 rounded-xl ${activePersona.avatarBg} flex items-center justify-center text-lg shadow-xs`}>
                  {activePersona.emoji}
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

              <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-500 bg-emerald-500/10 px-3 py-1.5 rounded-full border border-emerald-500/20">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
                RAG Context Active
              </div>
            </div>

            {/* Chat Messages */}
            <div className="p-6 md:p-8 space-y-4 min-h-[300px] max-h-[400px] overflow-y-auto bg-card">
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
                    className="text-xs bg-card hover:bg-muted border border-border text-foreground px-3.5 py-2 rounded-xl transition-all text-left flex items-center gap-1.5 shadow-xs disabled:opacity-50 hover:border-primary/30"
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
              Customize the accent color, header title, and screen position. The script snippet updates instantly — just copy and paste.
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
                      className={`w-9 h-9 rounded-full border-2 transition-all ${
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
                      className={`py-3 px-4 rounded-xl text-xs font-semibold border transition-all capitalize ${
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
                    className="text-primary hover:underline flex items-center gap-1 font-bold"
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
                    className="w-13 h-13 rounded-full shadow-xl flex items-center justify-center text-white hover:scale-110 transition-transform"
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
              Start for free—no credit card needed. Scale up only when your team needs more.
            </p>

            {/* Billing Toggle */}
            <div className="flex items-center justify-center gap-4 mt-8">
              <span className={`text-sm font-semibold ${!annualBilling ? 'text-foreground' : 'text-muted-foreground'}`}>Monthly</span>
              <button
                type="button"
                onClick={() => setAnnualBilling(!annualBilling)}
                className={`w-12 h-6 rounded-full transition-colors relative flex items-center p-0.5 ${annualBilling ? 'bg-primary' : 'bg-muted'}`}
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
              desc="Perfect for building your first AI assistant and exploring the platform."
              features={[
                "1 Workspace",
                "1 AI Assistant",
                "1,000 Messages / month",
                "100 MB Document Storage",
                "1 Website Chatbot Widget",
                "Community Support",
              ]}
            />
            <PricingCard
              title="Pro"
              priceInr={annualBilling ? "799" : "999"}
              priceUsd={annualBilling ? "10" : "12"}
              desc="For creators and teams who need more agents, more messages, and priority support."
              features={[
                "3 Workspaces",
                "5 AI Assistants",
                "10,000 Messages / month",
                "1 GB Document Storage",
                "3 Website Chatbots",
                "Custom AI Models (BYOK)",
                "Priority Support",
              ]}
              isPopular
            />
            <PricingCard
              title="Business"
              priceInr={annualBilling ? "3,199" : "3,999"}
              priceUsd={annualBilling ? "39" : "49"}
              desc="For growing businesses with high volumes and advanced team collaboration needs."
              features={[
                "Unlimited Workspaces",
                "20 AI Assistants",
                "50,000 Messages / month",
                "10 GB Document Storage",
                "Unlimited Website Chatbots",
                "Advanced Team Roles & Permissions",
                "Dedicated Support",
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
            <Link
              to="/login"
              className="px-5 py-2.5 rounded-xl btn-primary text-xs font-bold shrink-0 shadow-md whitespace-nowrap"
            >
              View Billing →
            </Link>
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
                  className="w-full px-6 py-5 text-left font-bold text-base flex items-center justify-between gap-4 text-foreground hover:text-primary transition-colors"
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
              className="w-full btn-primary py-4 rounded-xl text-base font-bold shadow-lg hover:shadow-xl flex items-center justify-center gap-2.5 transition-all disabled:opacity-75"
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
            <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full border border-primary/30 bg-primary/8 text-primary text-xs font-bold uppercase tracking-wider mb-6">
              <Sparkles size={13} className="animate-pulse" /> Start Today
            </div>

            <h2 className="text-4xl md:text-6xl font-extrabold tracking-tight text-foreground leading-tight">
              Your documents are just
              <br />
              <span
                className="bg-clip-text text-transparent"
                style={{ backgroundImage: 'linear-gradient(135deg, #FF4D00 0%, #FF8C00 100%)' }}
              >
                sitting there.
              </span>
            </h2>

            <p className="mt-6 text-lg text-muted-foreground max-w-xl mx-auto leading-relaxed">
              Turn your PDFs, manuals, and policies into a brilliant AI assistant that works 24/7, 
              cites its sources, and deploys in under 10 minutes. For free.
            </p>

            <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link
                to="/login"
                className="w-full sm:w-auto btn-primary px-10 py-4 rounded-full text-base font-bold shadow-lg hover:shadow-xl hover:scale-[1.03] transition-all flex items-center justify-center gap-2 group"
              >
                <Rocket size={18} />
                Build Your AI Assistant — Free
                <ArrowRight size={18} className="group-hover:translate-x-0.5 transition-transform" />
              </Link>
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
                <li><Link to="/user-guide" className="hover:text-primary transition-colors">User Documentation</Link></li>
                <li><Link to="/blog" className="hover:text-primary transition-colors">Product Blog</Link></li>
                <li><Link to="/login" className="hover:text-primary transition-colors">Studio Console</Link></li>
              </ul>
            </div>

            <div>
              <h4 className="font-bold text-sm uppercase tracking-wider mb-5 text-foreground">Company</h4>
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

      <Link
        to="/login"
        className={`w-full text-center py-3.5 rounded-xl font-bold text-sm transition-all ${
          isPopular
            ? 'btn-primary shadow-md hover:shadow-lg'
            : 'bg-muted/50 hover:bg-muted border border-border text-foreground'
        }`}
      >
        {priceInr === "0" ? "Get Started Free" : `Upgrade to ${title}`}
      </Link>
    </div>
  );
}

// ─── AgentNode Sub-Component ────────────────────────────────────────────────
// Renders a single agent node card on the Studio canvas, faithfully recreating
// the real BlinkBot Studio UI. Each node represents one AI agent in the network.
//
// Props:
//   title    — agent display name
//   subtitle — role / model / tool description line
//   style    — React inline style for absolute positioning { top, left }
//   active   — shows a blue "active" indicator dot
//   pulse    — adds an animated ping ring (for the supervisor/live node)
//   selected — applies purple glow border (matches the real "selected node" state)
//   toggleOn — renders the blue toggle in the ON position (enabled agent)
function AgentNode({ title, subtitle, style, active, pulse, selected, toggleOn }) {
  return (
    <div className="absolute" style={{ ...style, zIndex: 5 }}>
      <div
        className={`w-44 rounded-2xl border p-3.5 cursor-default transition-all ${
          selected
            ? 'border-[#7C3AED] bg-[#1a0e2e] shadow-[0_0_28px_rgba(124,58,237,0.5)]'
            : 'border-[#30363d] bg-[#161b22] shadow-lg'
        }`}
      >
        {/* Header: active indicator dot + agent name + toggle switch */}
        <div className="flex items-center gap-2 mb-2">
          {/* Live/active dot with optional ping animation */}
          <div className="relative shrink-0">
            <div
              className={`w-2 h-2 rounded-full ${
                active ? 'bg-blue-400' : selected ? 'bg-violet-400' : 'bg-slate-500'
              }`}
            />
            {pulse && (
              <div className="absolute inset-0 w-2 h-2 rounded-full bg-blue-400 animate-ping opacity-60" />
            )}
          </div>

          {/* Agent title */}
          <span className="text-[10px] font-bold text-white truncate flex-1">{title}</span>

          {/* Blue toggle in ON position */}
          {toggleOn && (
            <div className="w-7 h-4 rounded-full bg-blue-500 flex items-center justify-end pr-0.5 shrink-0 shadow-sm">
              <div className="w-3 h-3 rounded-full bg-white shadow" />
            </div>
          )}
        </div>

        {/* Subtitle / role description */}
        <div className="text-[9px] text-slate-500 leading-snug mb-3 truncate">{subtitle}</div>

        {/* Settings action button */}
        <button
          className={`w-full text-[9px] font-semibold py-1.5 rounded-lg flex items-center justify-center gap-1 transition-colors ${
            selected
              ? 'bg-[#7C3AED]/30 text-violet-300 border border-[#7C3AED]/40'
              : 'bg-white/5 text-slate-400 border border-[#30363d] hover:bg-white/10'
          }`}
        >
          <Settings size={9} /> Settings
        </button>
      </div>
    </div>
  );
}

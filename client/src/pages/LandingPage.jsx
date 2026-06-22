import { useState } from 'react';
import { usePageSeo } from '../hooks/usePageSeo';
import { Link } from 'react-router-dom';
import { 
  Bot, Zap, Database, Globe, ArrowRight, ShieldCheck, Cpu, Sun, Moon, 
  Sparkles, BarChart3, Users, Upload, Settings, Code, Brain, 
  MessageSquare, ChevronRight, Check, Send, Loader2, Star,
  Search, Layers, RefreshCw
} from 'lucide-react';
import Logo from '../components/shared/Logo';
import { useUIStore } from "../store/useUIStore";
import { toast } from 'sonner';

const API_URL = import.meta.env.VITE_API_BASE_URL || '';

export default function LandingPage() {
  usePageSeo(); // Uses global default title & description
  const darkMode = useUIStore((state) => state.darkMode);
  const toggleDarkMode = useUIStore((state) => state.toggleDarkMode);

  const [demoForm, setDemoForm] = useState({ name: '', email: '', company: '', message: '' });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleDemoSubmit = async (e) => {
    e.preventDefault();
    if (!demoForm.name.trim() || !demoForm.email.trim()) {
      toast.error("Name and Email are required.");
      return;
    }
    setIsSubmitting(true);
    try {
      const res = await fetch(`${API_URL}/api/demo-request`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(demoForm),
      });
      if (!res.ok) throw new Error('Failed to submit');
      toast.success("Demo request submitted! We'll get back to you soon.");
      setDemoForm({ name: '', email: '', company: '', message: '' });
    } catch {
      toast.error("Something went wrong. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground font-sans selection:bg-primary/30 overflow-x-hidden">
      {/* ═══════════════════════ NAVIGATION ═══════════════════════ */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-background/70 backdrop-blur-xl border-b border-border/30">
        <div className="flex items-center justify-between px-6 md:px-8 py-4 max-w-7xl mx-auto">
          <Logo />
          <div className="flex items-center gap-3 md:gap-5">
            <a href="#features" className="hidden md:inline text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">Features</a>
            <a href="#how-it-works" className="hidden md:inline text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">How It Works</a>
            <a href="#pricing" className="hidden md:inline text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">Pricing</a>
            <a href="#demo" className="hidden md:inline text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">Book a Demo</a>
            <button
              onClick={toggleDarkMode}
              type="button"
              className="h-9 w-9 rounded-lg border border-border/50 text-muted-foreground flex items-center justify-center hover:bg-muted hover:text-foreground transition-all"
            >
              {darkMode ? <Sun size={16} /> : <Moon size={16} />}
            </button>
            <Link to="/login" className="text-sm font-semibold hover:text-primary transition-colors hidden sm:inline">
              Log in
            </Link>
            <Link to="/login" className="btn-primary px-5 py-2 rounded-full text-sm font-bold shadow-lg shadow-primary/20 hover:shadow-primary/40 transition-all">
              Get Started Free
            </Link>
          </div>
        </div>
      </nav>

      {/* ═══════════════════════ HERO ═══════════════════════ */}
      <section className="relative pt-32 md:pt-40 pb-24 md:pb-32 flex flex-col items-center text-center px-6">
        {/* Gradient orbs */}
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-primary/15 blur-[150px] rounded-full pointer-events-none" />
        <div className="absolute bottom-0 right-0 w-[400px] h-[400px] bg-purple-500/10 blur-[120px] rounded-full pointer-events-none" />

        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-primary/30 bg-primary/10 text-primary text-sm font-semibold mb-8 backdrop-blur-md">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
          </span>
          Now in Public Beta — Start for Free
        </div>

        <h1 className="text-4xl sm:text-5xl md:text-7xl font-extrabold tracking-tight max-w-5xl leading-[1.1]">
          Your Custom AI Bots{' '}
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary via-purple-500 to-pink-500">
            Built in Minutes
          </span>
        </h1>

        <p className="mt-6 md:mt-8 text-lg md:text-xl text-muted-foreground max-w-2xl leading-relaxed">
          Upload your documents, configure with AI, and deploy powerful conversational bots to your website — no code required.
        </p>

        <div className="mt-10 flex flex-col sm:flex-row items-center gap-4">
          <Link to="/login" className="btn-primary px-8 py-4 rounded-full text-lg font-bold shadow-xl shadow-primary/25 hover:shadow-primary/40 hover:scale-[1.02] transition-all flex items-center gap-2">
            Start Building Free <ArrowRight size={20} />
          </Link>
          <a href="#demo" className="px-8 py-4 rounded-full text-lg font-semibold border border-border hover:bg-muted transition-all flex items-center gap-2">
            Book a Demo <ChevronRight size={18} />
          </a>
        </div>

        {/* Mock UI Preview */}
        <div className="mt-16 md:mt-20 w-full max-w-4xl mx-auto relative">
          <div className="absolute inset-0 bg-gradient-to-b from-primary/10 to-purple-500/10 rounded-[32px] blur-3xl -z-10 scale-105" />
          <div className="bg-card border border-border/50 rounded-[24px] shadow-2xl overflow-hidden">
            {/* Fake browser bar */}
            <div className="flex items-center gap-2 px-5 py-3 border-b border-border/50 bg-muted/30">
              <div className="flex gap-1.5">
                <div className="h-3 w-3 rounded-full bg-red-400/80"></div>
                <div className="h-3 w-3 rounded-full bg-yellow-400/80"></div>
                <div className="h-3 w-3 rounded-full bg-green-400/80"></div>
              </div>
              <div className="flex-1 mx-4">
                <div className="bg-background border border-border/50 rounded-lg px-4 py-1.5 text-xs text-muted-foreground text-center">app.blinkbot.ai/studio</div>
              </div>
            </div>
            {/* Content preview */}
            <div className="p-6 md:p-8 grid md:grid-cols-3 gap-4 min-h-[260px]">
              {/* Sidebar */}
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-sm font-semibold"><Bot size={16} className="text-primary" /> My Bots</div>
                {["Sales Assistant", "Support Bot", "Lead Qualifier"].map((name, i) => (
                  <div key={i} className={`flex items-center gap-2 p-2.5 rounded-xl text-sm transition-all ${i === 0 ? 'bg-primary/10 text-primary font-medium' : 'text-muted-foreground hover:bg-muted/50'}`}>
                    <div className={`h-2 w-2 rounded-full ${i === 0 ? 'bg-green-500' : 'bg-muted-foreground/30'}`} />
                    {name}
                  </div>
                ))}
              </div>
              {/* Chat area */}
              <div className="md:col-span-2 space-y-3">
                <div className="flex items-start gap-3">
                  <div className="w-7 h-7 rounded-full bg-primary flex items-center justify-center shrink-0"><Bot size={14} className="text-white" /></div>
                  <div className="bg-muted/50 border border-border/30 p-3 rounded-2xl rounded-tl-sm text-sm max-w-[80%]">
                    Based on your product catalog, the MacBook Pro 16" M3 is currently available at ₹2,49,900 with free delivery. Shall I help you place an order?
                  </div>
                </div>
                <div className="flex items-start gap-3 flex-row-reverse">
                  <div className="w-7 h-7 rounded-full bg-blue-500 flex items-center justify-center shrink-0"><span className="text-white text-[10px] font-bold">U</span></div>
                  <div className="bg-primary/10 border border-primary/20 p-3 rounded-2xl rounded-tr-sm text-sm max-w-[80%]">
                    Yes! Also, what's the warranty policy?
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="w-7 h-7 rounded-full bg-primary flex items-center justify-center shrink-0"><Bot size={14} className="text-white" /></div>
                  <div className="bg-muted/50 border border-border/30 p-3 rounded-2xl rounded-tl-sm text-sm max-w-[80%] flex items-center gap-2">
                    <Loader2 size={14} className="animate-spin text-primary" /> Searching your documents...
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════════════════ FEATURES ═══════════════════════ */}
      <section id="features" className="py-20 md:py-28 border-y border-border/30">
        <div className="max-w-7xl mx-auto px-6 md:px-8">
          <div className="text-center mb-16">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-bold uppercase tracking-wider mb-4">
              <Sparkles size={14} /> Platform Features
            </div>
            <h2 className="text-3xl md:text-5xl font-extrabold tracking-tight">Everything you need to deploy AI bots.</h2>
            <p className="mt-4 text-muted-foreground text-lg max-w-2xl mx-auto">Powerful features wrapped in an incredibly simple interface. No coding required.</p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            <FeatureCard 
              icon={Layers} 
              title="4-Step Bot Builder" 
              desc="Create custom AI bots with our guided wizard — set identity, behavior, knowledge, and model in under 2 minutes."
              color="from-blue-500/20 to-cyan-500/20"
              iconColor="text-blue-500"
            />
            <FeatureCard 
              icon={Sparkles} 
              title="AI Auto-Configure" 
              desc="Describe your bot in one sentence and our Meta-Agent writes the name, system prompt, and output format automatically."
              color="from-purple-500/20 to-pink-500/20"
              iconColor="text-purple-500"
            />
            <FeatureCard 
              icon={Database} 
              title="Instant Knowledge Base" 
              desc="Upload PDFs, CSVs, TXT files or paste website URLs. We chunk, embed, and index your data into a vector database instantly."
              color="from-emerald-500/20 to-teal-500/20"
              iconColor="text-emerald-500"
            />
            <FeatureCard 
              icon={Globe} 
              title="Embeddable Chat Widget" 
              desc="Generate an HTML snippet and embed your bot on any website in 30 seconds. Supports React components and REST API too."
              color="from-orange-500/20 to-amber-500/20"
              iconColor="text-orange-500"
            />
            <FeatureCard 
              icon={BarChart3} 
              title="Analytics & Insights" 
              desc="Track message volumes, response times, agent performance, and conversation trends with real-time charts and metrics."
              color="from-rose-500/20 to-red-500/20"
              iconColor="text-rose-500"
            />
            <FeatureCard 
              icon={Users} 
              title="Team Collaboration" 
              desc="Invite team members, assign roles (Admin/Member), and manage multiple workspaces. Everyone works in a secure silo."
              color="from-indigo-500/20 to-violet-500/20"
              iconColor="text-indigo-500"
            />
          </div>
        </div>
      </section>

      {/* ═══════════════════════ HOW IT WORKS ═══════════════════════ */}
      <section id="how-it-works" className="py-20 md:py-28 bg-muted/10">
        <div className="max-w-6xl mx-auto px-6 md:px-8">
          <div className="text-center mb-16">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 text-xs font-bold uppercase tracking-wider mb-4">
              <Zap size={14} /> How It Works
            </div>
            <h2 className="text-3xl md:text-5xl font-extrabold tracking-tight">Three steps. Zero complexity.</h2>
          </div>

          <div className="grid md:grid-cols-3 gap-8 md:gap-12">
            <StepCard number="01" title="Upload Your Data" desc="Drag & drop your PDFs, CSVs, or paste any website URL. We automatically chunk and embed everything into a high-performance vector database." icon={Upload} />
            <StepCard number="02" title="Configure Your Bot" desc="Choose from Groq, OpenAI, or Ollama models. Set a system prompt, define output format, and enable web search fallback — or let AI configure it for you." icon={Settings} />
            <StepCard number="03" title="Deploy Anywhere" desc="Embed a customizable chat widget on your website with one line of code, use our React component, or integrate via REST API." icon={Code} />
          </div>
        </div>
      </section>

      {/* ═══════════════════════ WHY BLINKBOT ═══════════════════════ */}
      <section className="py-20 md:py-28">
        <div className="max-w-7xl mx-auto px-6 md:px-8">
          <div className="grid md:grid-cols-2 gap-12 md:gap-16 items-center">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-purple-500/10 text-purple-600 dark:text-purple-400 text-xs font-bold uppercase tracking-wider mb-6">
                <ShieldCheck size={14} /> Why BlinkBot
              </div>
              <h2 className="text-3xl md:text-4xl font-extrabold tracking-tight mb-8">Built different. Built better.</h2>
              <ul className="space-y-6">
                <Differentiator icon={Cpu} title="Multi-Provider LLMs" desc="Groq, OpenAI, Ollama — use any provider. Never locked in. Switch models on the fly." />
                <Differentiator icon={ShieldCheck} title="Privacy First" desc="Your data is never used to train public models. Embeddings are stored securely in your workspace." />
                <Differentiator icon={RefreshCw} title="Self-Learning Bots" desc="Users can flag wrong answers. The feedback loop auto-corrects bot behavior with memory patching." />
                <Differentiator icon={Search} title="Web Search Fallback" desc="When docs don't have the answer, bots automatically search the web for accurate responses." />
              </ul>
            </div>

            {/* Interactive demo card */}
            <div className="relative">
              <div className="absolute inset-0 bg-gradient-to-br from-primary/20 to-purple-500/20 rounded-[32px] blur-3xl -z-10" />
              <div className="bg-card border border-border/50 rounded-[28px] p-6 md:p-8 shadow-2xl space-y-5">
                <div className="flex items-center gap-3 mb-2">
                  <div className="h-10 w-10 rounded-xl bg-primary flex items-center justify-center"><Bot size={22} className="text-white" /></div>
                  <div>
                    <h4 className="font-bold">Support Agent</h4>
                    <p className="text-xs text-muted-foreground">Trained on 47 documents • 12 web pages</p>
                  </div>
                  <div className="ml-auto flex items-center gap-1 text-xs text-emerald-500 font-semibold"><span className="h-2 w-2 bg-emerald-500 rounded-full" /> Online</div>
                </div>
                <div className="space-y-3">
                  <div className="flex items-start gap-3">
                    <div className="w-7 h-7 rounded-full bg-primary flex items-center justify-center shrink-0"><Bot size={14} className="text-white" /></div>
                    <div className="bg-muted/50 p-3 rounded-2xl rounded-tl-sm text-sm">Hello! I've read all 47 company documents. How can I assist you today?</div>
                  </div>
                  <div className="flex items-start gap-3 flex-row-reverse">
                    <div className="w-7 h-7 rounded-full bg-blue-500 flex items-center justify-center shrink-0"><span className="text-white text-[10px] font-bold">U</span></div>
                    <div className="bg-primary/10 border border-primary/20 p-3 rounded-2xl rounded-tr-sm text-sm">What's our refund policy for enterprise clients?</div>
                  </div>
                  <div className="flex items-start gap-3">
                    <div className="w-7 h-7 rounded-full bg-primary flex items-center justify-center shrink-0"><Bot size={14} className="text-white" /></div>
                    <div className="bg-muted/50 p-3 rounded-2xl rounded-tl-sm text-sm">
                      According to the <span className="text-primary font-medium">Enterprise Handbook (p.23)</span>, enterprise clients are eligible for a full refund within 30 days of purchase. After 30 days, a prorated refund applies.
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2 pt-2 border-t border-border/30">
                  <div className="flex-1 bg-muted/30 border border-border/30 rounded-xl px-4 py-2.5 text-sm text-muted-foreground">Ask a follow-up question...</div>
                  <button className="h-10 w-10 rounded-xl bg-primary flex items-center justify-center"><Send size={16} className="text-white" /></button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════════════════ PRICING PREVIEW ═══════════════════════ */}
      <section id="pricing" className="py-20 md:py-28 bg-muted/10 border-y border-border/30">
        <div className="max-w-6xl mx-auto px-6 md:px-8">
          <div className="text-center mb-16">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-500/10 text-amber-600 dark:text-amber-400 text-xs font-bold uppercase tracking-wider mb-4">
              <Star size={14} /> Pricing
            </div>
            <h2 className="text-3xl md:text-5xl font-extrabold tracking-tight">Simple, transparent pricing.</h2>
            <p className="mt-4 text-muted-foreground text-lg">Start free. Scale as you grow. No hidden fees.</p>
          </div>

          <div className="grid md:grid-cols-3 gap-6 md:gap-8">
            <PricingCard title="Starter" price="0" desc="Perfect for exploring BlinkBot." features={["1 AI Bot", "1,000 Messages/mo", "100 MB Storage", "Community Support"]} />
            <PricingCard title="Pro" price="24" desc="For teams and power users." features={["5 AI Bots", "10,000 Messages/mo", "500 MB Storage", "2 Chat Widgets", "Priority Support"]} isPopular />
            <PricingCard title="Enterprise" price="120" desc="For organizations at scale." features={["20 AI Bots", "100,000 Messages/mo", "5 GB Storage", "10 Chat Widgets", "Custom Plan Builder"]} />
          </div>

          <div className="text-center mt-10">
            <Link to="/login" className="text-primary font-semibold hover:underline inline-flex items-center gap-1">
              View full pricing & custom plan builder <ArrowRight size={16} />
            </Link>
          </div>
        </div>
      </section>

      {/* ═══════════════════════ BOOK A DEMO ═══════════════════════ */}
      <section id="demo" className="py-20 md:py-28">
        <div className="max-w-3xl mx-auto px-6 md:px-8">
          <div className="text-center mb-12">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-bold uppercase tracking-wider mb-4">
              <MessageSquare size={14} /> Book a Demo
            </div>
            <h2 className="text-3xl md:text-4xl font-extrabold tracking-tight">See BlinkBot in action.</h2>
            <p className="mt-4 text-muted-foreground text-lg">Fill out the form and we'll schedule a personalized walkthrough of the platform.</p>
          </div>

          <form onSubmit={handleDemoSubmit} className="bg-card border border-border/50 rounded-[28px] p-6 md:p-10 shadow-xl space-y-5">
            <div className="grid sm:grid-cols-2 gap-5">
              <div>
                <label className="text-sm font-semibold block mb-2">Full Name <span className="text-red-500">*</span></label>
                <input
                  type="text"
                  value={demoForm.name}
                  onChange={(e) => setDemoForm({...demoForm, name: e.target.value})}
                  className="w-full border border-border bg-background rounded-xl px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-primary/30 transition"
                  placeholder="John Doe"
                  required
                />
              </div>
              <div>
                <label className="text-sm font-semibold block mb-2">Work Email <span className="text-red-500">*</span></label>
                <input
                  type="email"
                  value={demoForm.email}
                  onChange={(e) => setDemoForm({...demoForm, email: e.target.value})}
                  className="w-full border border-border bg-background rounded-xl px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-primary/30 transition"
                  placeholder="john@company.com"
                  required
                />
              </div>
            </div>
            <div>
              <label className="text-sm font-semibold block mb-2">Company</label>
              <input
                type="text"
                value={demoForm.company}
                onChange={(e) => setDemoForm({...demoForm, company: e.target.value})}
                className="w-full border border-border bg-background rounded-xl px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-primary/30 transition"
                placeholder="Acme Corp"
              />
            </div>
            <div>
              <label className="text-sm font-semibold block mb-2">How can we help?</label>
              <textarea
                rows={4}
                value={demoForm.message}
                onChange={(e) => setDemoForm({...demoForm, message: e.target.value})}
                className="w-full border border-border bg-background rounded-xl px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-primary/30 resize-y transition"
                placeholder="Tell us about your use case..."
              />
            </div>
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full btn-primary py-4 rounded-xl text-base font-bold shadow-lg shadow-primary/20 hover:shadow-primary/40 flex items-center justify-center gap-2 disabled:opacity-70 transition-all"
            >
              {isSubmitting ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
              {isSubmitting ? "Submitting..." : "Request a Demo"}
            </button>
          </form>
        </div>
      </section>

      {/* ═══════════════════════ FOOTER ═══════════════════════ */}
      <footer className="border-t border-border/50 bg-muted/10">
        <div className="max-w-7xl mx-auto px-6 md:px-8 py-16">
          <div className="grid md:grid-cols-4 gap-10 md:gap-16">
            {/* Brand */}
            <div className="md:col-span-1">
              <Logo />
              <p className="text-sm text-muted-foreground mt-4 leading-relaxed">
                Build, deploy, and manage custom AI bots powered by your own data. No code required.
              </p>
            </div>

            {/* Product */}
            <div>
              <h4 className="font-bold text-sm uppercase tracking-wider mb-4">Product</h4>
              <ul className="space-y-2.5 text-sm text-muted-foreground">
                <li><a href="#features" className="hover:text-foreground transition-colors">Features</a></li>
                <li><a href="#pricing" className="hover:text-foreground transition-colors">Pricing</a></li>
                <li><a href="#how-it-works" className="hover:text-foreground transition-colors">How It Works</a></li>
                <li><a href="#demo" className="hover:text-foreground transition-colors">Book a Demo</a></li>
              </ul>
            </div>

            {/* Resources */}
            <div>
              <h4 className="font-bold text-sm uppercase tracking-wider mb-4">Resources</h4>
              <ul className="space-y-2.5 text-sm text-muted-foreground">
                <li><Link to="/user-guide" className="hover:text-foreground transition-colors">User Guide</Link></li>
                <li><Link to="/blog" className="hover:text-foreground transition-colors">Blog</Link></li>
                <li><Link to="/login" className="hover:text-foreground transition-colors">Dashboard</Link></li>
              </ul>
            </div>

            {/* Company */}
            <div>
              <h4 className="font-bold text-sm uppercase tracking-wider mb-4">Company</h4>
              <ul className="space-y-2.5 text-sm text-muted-foreground">
                <li><Link to="/about" className="hover:text-foreground transition-colors">About Us</Link></li>
                <li><Link to="/terms" className="hover:text-foreground transition-colors">Terms & Conditions</Link></li>
                <li><a href="mailto:techmate.ed@gmail.com" className="hover:text-foreground transition-colors">Contact</a></li>
              </ul>
            </div>
          </div>

          <div className="border-t border-border/30 mt-12 pt-8 flex flex-col sm:flex-row items-center justify-between gap-4">
            <p className="text-sm text-muted-foreground">© {new Date().getFullYear()} BlinkBot. Built for the future of AI.</p>
            <div className="flex items-center gap-4 text-sm text-muted-foreground">
              <Link to="/terms" className="hover:text-foreground transition-colors">Terms</Link>
              <Link to="/about" className="hover:text-foreground transition-colors">About</Link>
              <a href="mailto:techmate.ed@gmail.com" className="hover:text-foreground transition-colors">Contact</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

/* ═══════════════════════ SUB-COMPONENTS ═══════════════════════ */

function FeatureCard({ icon: Icon, title, desc, color, iconColor }) {
  return (
    <div className="group bg-card border border-border/50 rounded-[20px] p-7 hover:border-primary/40 hover:-translate-y-1 hover:shadow-xl transition-all duration-300">
      <div className={`w-12 h-12 rounded-2xl bg-gradient-to-br ${color} flex items-center justify-center mb-5`}>
        <Icon size={24} className={iconColor} />
      </div>
      <h3 className="text-lg font-bold mb-2">{title}</h3>
      <p className="text-sm text-muted-foreground leading-relaxed">{desc}</p>
    </div>
  );
}

function StepCard({ number, title, desc, icon: Icon }) {
  return (
    <div className="relative text-center group">
      <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-primary/10 text-primary mb-6 group-hover:scale-110 transition-transform">
        <Icon size={28} />
      </div>
      <div className="text-6xl font-black text-primary/10 absolute -top-4 -left-2 md:left-auto md:-top-6 select-none pointer-events-none">{number}</div>
      <h3 className="text-xl font-bold mb-3">{title}</h3>
      <p className="text-sm text-muted-foreground leading-relaxed">{desc}</p>
    </div>
  );
}

function Differentiator({ icon: Icon, title, desc }) {
  return (
    <li className="flex gap-4">
      <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center shrink-0 mt-0.5">
        <Icon size={20} className="text-primary" />
      </div>
      <div>
        <h4 className="font-bold mb-1">{title}</h4>
        <p className="text-sm text-muted-foreground leading-relaxed">{desc}</p>
      </div>
    </li>
  );
}

function PricingCard({ title, price, desc, features, isPopular }) {
  return (
    <div className={`relative bg-card border rounded-[24px] p-7 flex flex-col transition-all hover:-translate-y-1 hover:shadow-xl ${isPopular ? 'border-primary shadow-lg shadow-primary/10 scale-[1.02]' : 'border-border/50'}`}>
      {isPopular && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2">
          <span className="bg-primary text-white text-[10px] font-bold px-3 py-1 rounded-full uppercase tracking-wider">Most Popular</span>
        </div>
      )}
      <h3 className="text-xl font-bold">{title}</h3>
      <p className="text-sm text-muted-foreground mt-1">{desc}</p>
      <div className="mt-5 mb-6">
        <span className="text-4xl font-extrabold">${price}</span>
        <span className="text-muted-foreground">/month</span>
      </div>
      <ul className="space-y-2.5 flex-1">
        {features.map((f, i) => (
          <li key={i} className="flex items-center gap-2.5 text-sm">
            <Check size={16} className="text-emerald-500 shrink-0" />
            {f}
          </li>
        ))}
      </ul>
      <Link to="/login" className={`mt-6 block text-center py-3 rounded-xl font-semibold text-sm transition-all ${isPopular ? 'btn-primary shadow-lg shadow-primary/20' : 'border border-border hover:bg-muted'}`}>
        {price === "0" ? "Start Free" : "Get Started"}
      </Link>
    </div>
  );
}

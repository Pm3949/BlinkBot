import { Link } from 'react-router-dom';
import { Bot, Zap, Database, Globe, ArrowRight, ShieldCheck, Cpu, Sun, Moon } from 'lucide-react';
import Logo from '../components/shared/Logo';
import { useUIStore } from "../store/useUIStore";

export default function LandingPage() {
  const darkMode = useUIStore((state) => state.darkMode);
  const toggleDarkMode = useUIStore((state) => state.toggleDarkMode);

  return (
    <div className="min-h-screen bg-background text-foreground font-sans selection:bg-primary/30">
      {/* Navigation */}
      <nav className="flex items-center justify-between px-8 py-6 max-w-7xl mx-auto">
        <Logo />
        <div className="flex items-center gap-6">
          <button
            onClick={toggleDarkMode}
            type="button"
            className="h-10 w-10 rounded-xl border border-border text-muted-foreground flex items-center justify-center hover:bg-muted hover:text-foreground transition-all"
          >
            {darkMode ? <Sun size={18} /> : <Moon size={18} />}
          </button>
          <Link to="/login" className="text-sm font-semibold hover:text-primary transition-colors">
            Log in
          </Link>
          <Link to="/login" className="btn-primary px-5 py-2.5 rounded-full text-sm font-bold shadow-lg shadow-primary/20 hover:shadow-primary/40 transition-all">
            Get Started Free
          </Link>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative pt-24 pb-32 overflow-hidden flex flex-col items-center text-center px-4">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-primary/20 blur-[120px] rounded-full pointer-events-none" />
        
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-primary/30 bg-primary/10 text-primary text-sm font-semibold mb-8 backdrop-blur-md">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
          </span>
          RAGMate 1.0 is Live
        </div>
        
        <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight max-w-4xl leading-tight text-foreground">
          Build Custom AI Agents <br/>
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary to-purple-500">
            On Your Own Data
          </span>
        </h1>
        
        <p className="mt-8 text-xl text-muted-foreground max-w-2xl">
          Instantly connect your internal documents, scrape your website, and deploy powerful conversational AI agents that actually know your business.
        </p>
        
        <div className="mt-12 flex flex-col sm:flex-row items-center gap-4">
          <Link to="/login" className="btn-primary px-8 py-4 rounded-full text-lg font-bold shadow-xl shadow-primary/20 hover:scale-105 transition-all flex items-center gap-2">
            Start Building Free <ArrowRight size={20} />
          </Link>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-24 bg-muted/20 border-y border-border/50">
        <div className="max-w-7xl mx-auto px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-5xl font-bold">Everything you need to deploy AI.</h2>
            <p className="mt-4 text-muted-foreground text-lg">Powerful features wrapped in an incredibly simple interface.</p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <FeatureCard 
              icon={Database} 
              title="Instant Knowledge Base" 
              desc="Drag and drop PDFs, docs, or paste website URLs. We automatically chunk, embed, and store your data in a high-performance vector database."
            />
            <FeatureCard 
              icon={Cpu} 
              title="Bring Your Own LLM" 
              desc="We don't lock you in. Connect your own Groq or OpenAI API keys and choose the exact model you want your agent to use."
            />
            <FeatureCard 
              icon={Globe} 
              title="Website Chat Widgets" 
              desc="Generate a simple HTML snippet and embed your custom AI agent directly onto your website in less than 30 seconds."
            />
          </div>
        </div>
      </section>

      {/* Differentiators Section */}
      <section className="py-24">
        <div className="max-w-7xl mx-auto px-8">
          <div className="grid md:grid-cols-2 gap-16 items-center">
            <div>
              <h2 className="text-4xl font-bold mb-6">Why RAGMate?</h2>
              <ul className="space-y-6">
                <Differentiator 
                  icon={ShieldCheck} 
                  title="Complete Privacy & Security" 
                  desc="Your data stays yours. RAGMate securely stores embeddings and never uses your internal documents to train external public models."
                />
                <Differentiator 
                  icon={Zap} 
                  title="Blazing Fast Retrieval" 
                  desc="Powered by optimized hybrid search combining semantic vector retrieval with keyword matching for the most accurate responses."
                />
                <Differentiator 
                  icon={Bot} 
                  title="Modular Architecture" 
                  desc="Swap out embedding models, chunking strategies, and language models on the fly to tune your agent's performance."
                />
              </ul>
            </div>
            <div className="relative">
              <div className="absolute inset-0 bg-gradient-to-br from-primary/20 to-purple-500/20 rounded-[40px] blur-3xl -z-10" />
              <div className="glass-card border border-border/50 rounded-[40px] p-8 shadow-2xl">
                <div className="space-y-4">
                  <div className="flex items-start gap-4">
                    <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center shrink-0">
                      <Bot size={18} className="text-primary-foreground" />
                    </div>
                    <div className="bg-muted p-4 rounded-2xl rounded-tl-sm text-sm">
                      Hello! I'm your custom agent. I have read all 40 of your company documents. How can I help you today?
                    </div>
                  </div>
                  <div className="flex items-start gap-4 flex-row-reverse">
                    <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center shrink-0">
                      <span className="text-white text-xs font-bold">U</span>
                    </div>
                    <div className="bg-primary/10 border border-primary/20 p-4 rounded-2xl rounded-tr-sm text-sm">
                      What is our company's refund policy according to the handbook?
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Coming Soon Roadmap */}
      <section className="py-24 bg-muted/20 border-t border-border/50">
        <div className="max-w-7xl mx-auto px-8 text-center">
          <h2 className="text-3xl font-bold mb-12">What's Coming Next?</h2>
          <div className="grid md:grid-cols-4 gap-6">
            <RoadmapCard title="Lead Generation" desc="Collect user emails directly inside the widget before chats begin." />
            <RoadmapCard title="Developer API" desc="Generate API keys to interact with your custom agents programmatically." />
            <RoadmapCard title="Agent Tools" desc="Allow agents to search the live web if they can't find answers in your docs." />
            <RoadmapCard title="Analytics 2.0" desc="Advanced transcript viewing and conversation sentiment analysis." />
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 border-t border-border/50 text-center text-muted-foreground flex flex-col items-center gap-4">
        <div className="flex items-center gap-6 text-sm font-medium">
          <Link to="/user-guide" className="hover:text-foreground transition-colors">User Guide</Link>
          <Link to="/terms" className="hover:text-foreground transition-colors">Terms & Conditions</Link>
        </div>
        <p>© {new Date().getFullYear()} RAGMate. Built for the future of AI.</p>
      </footer>
    </div>
  );
}

function FeatureCard({ icon: Icon, title, desc }) {
  return (
    <div className="glass-card p-8 border border-border/50 hover:border-primary/50 transition-all hover:-translate-y-1">
      <div className="w-14 h-14 rounded-2xl bg-primary/10 flex items-center justify-center mb-6">
        <Icon size={28} className="text-primary" />
      </div>
      <h3 className="text-xl font-bold mb-3">{title}</h3>
      <p className="text-muted-foreground leading-relaxed">{desc}</p>
    </div>
  );
}

function Differentiator({ icon: Icon, title, desc }) {
  return (
    <li className="flex gap-4">
      <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center shrink-0 mt-1">
        <Icon size={20} className="text-primary" />
      </div>
      <div>
        <h4 className="text-lg font-bold mb-1">{title}</h4>
        <p className="text-muted-foreground">{desc}</p>
      </div>
    </li>
  );
}

function RoadmapCard({ title, desc }) {
  return (
    <div className="p-6 border border-border/50 bg-background rounded-3xl opacity-80">
      <div className="inline-block px-3 py-1 rounded-full bg-blue-500/10 text-blue-500 text-xs font-bold mb-4 uppercase tracking-wider">
        Coming Soon
      </div>
      <h4 className="font-bold mb-2">{title}</h4>
      <p className="text-sm text-muted-foreground">{desc}</p>
    </div>
  );
}

import React, { useState, useEffect } from 'react';
import { usePageSeo } from '../hooks/usePageSeo';
import { Link, useLocation } from 'react-router-dom';
import { 
  ChevronLeft, BookOpen, Bot, Database, Globe, Users, BarChart3, 
  CreditCard, Settings, MessageSquare, Sparkles, Brain, Code,
  Upload, Layers, RefreshCw, Search, Shield, ChevronRight
} from 'lucide-react';
import Logo from '../components/shared/Logo';

const sections = [
  { id: "introduction", label: "Introduction", icon: BookOpen },
  { id: "account-setup", label: "Account & Workspaces", icon: Users },
  { id: "creating-bots", label: "Creating AI Bots", icon: Bot },
  { id: "ai-auto-configure", label: "AI Auto-Configure", icon: Sparkles },
  { id: "knowledge-base", label: "Knowledge Base", icon: Database },
  { id: "studio", label: "Agent Studio", icon: MessageSquare },
  { id: "agent-networks", label: "Agent Networks", icon: Layers },
  { id: "chat-widgets", label: "Chat Widgets", icon: Globe },
  { id: "analytics", label: "Analytics", icon: BarChart3 },
  { id: "feedback", label: "Feedback & Corrections", icon: RefreshCw },
  { id: "billing", label: "Billing & Plans", icon: CreditCard },
  { id: "languages", label: "Language Support", icon: Globe },
  { id: "faq", label: "FAQs", icon: Search },
];

export default function UserGuidePage() {
  usePageSeo('User Guide', 'Complete guide to building, configuring, and deploying custom AI chatbots with BlinkBot. From document upload to embedding a live widget.');
  const [activeSection, setActiveSection] = useState("introduction");

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setActiveSection(entry.target.id);
          }
        });
      },
      { rootMargin: "-20% 0px -70% 0px" }
    );

    sections.forEach(({ id }) => {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    });

    return () => observer.disconnect();
  }, []);

  return (
    <div className="min-h-screen bg-background text-foreground font-sans">
      {/* Nav */}
      <nav className="sticky top-0 z-40 bg-background/80 backdrop-blur-xl border-b border-border/50">
        <div className="flex items-center justify-between px-6 md:px-8 py-4 max-w-7xl mx-auto">
          <div className="flex items-center gap-4">
            <Link to="/" className="p-2 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-all">
              <ChevronLeft size={20} />
            </Link>
            <Logo />
          </div>
          <Link to="/login" className="btn-primary px-5 py-2 rounded-full text-sm font-bold shadow-lg shadow-primary/20">
            Get Started
          </Link>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-6 md:px-8 flex gap-8">
        {/* Sticky TOC Sidebar */}
        <aside className="hidden lg:block w-64 shrink-0">
          <nav className="sticky top-24 py-8 space-y-1 max-h-[calc(100vh-6rem)] overflow-y-auto pr-4">
            <h3 className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground mb-3 px-3">On this page</h3>
            {sections.map(({ id, label, icon: Icon }) => (
              <a
                key={id}
                href={`#${id}`}
                className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-all ${
                  activeSection === id 
                    ? 'bg-primary/10 text-primary font-semibold' 
                    : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
                }`}
              >
                <Icon size={14} className="shrink-0" />
                <span className="truncate">{label}</span>
              </a>
            ))}
          </nav>
        </aside>

        {/* Main Content */}
        <main className="flex-1 min-w-0 py-12 pb-24">
          <div className="mb-12">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                <BookOpen className="text-primary" size={20} />
              </div>
              <h1 className="text-4xl font-extrabold tracking-tight">User Guide</h1>
            </div>
            <p className="text-muted-foreground text-lg">Everything you need to know to build and deploy custom AI bots with BlinkBot.</p>
          </div>

          <div className="space-y-16">
            {/* 1. Introduction */}
            <GuideSection id="introduction" title="Introduction" icon={BookOpen}>
              <p>
                BlinkBot is an AI operating system that lets you build custom conversational bots powered by your own data. 
                Upload internal documents, scrape websites, configure LLM models, and deploy intelligent bots that answer 
                questions accurately — without hallucinating.
              </p>
              <p>
                Whether you're building a customer support bot, an internal knowledge assistant, or a sales qualification agent, 
                BlinkBot gives you all the tools to go from idea to deployment in minutes.
              </p>
              <InfoBox title="Key Highlights">
                <ul className="list-disc pl-5 space-y-1 text-sm">
                  <li>No coding required — visual 4-step wizard</li>
                  <li>Multi-provider LLMs: Groq, OpenAI, Ollama</li>
                  <li>Automatic document chunking & vector embedding</li>
                  <li>Embeddable chat widgets for any website</li>
                  <li>Self-learning feedback loops</li>
                  <li>Team collaboration with role-based access</li>
                </ul>
              </InfoBox>
            </GuideSection>

            {/* 2. Account Setup */}
            <GuideSection id="account-setup" title="Account Setup & Workspaces" icon={Users}>
              <p>
                When you sign up, you're automatically placed in a <strong>Workspace</strong>. A workspace is a secure, isolated 
                environment for your team where all agents, documents, and chatbots are contained.
              </p>
              <h4 className="font-bold mt-6 mb-2">Key Concepts:</h4>
              <ul className="list-disc pl-5 space-y-2 text-muted-foreground">
                <li><strong>Workspaces:</strong> Each workspace is a silo. Data from one workspace never leaks into another.</li>
                <li><strong>Team Members:</strong> Invite colleagues from the <strong>Team</strong> page. Choose between Admin and Member roles.</li>
                <li><strong>Admins:</strong> Can manage billing, team, and all platform settings.</li>
                <li><strong>Members:</strong> Can create agents, upload documents, and use the studio.</li>
              </ul>
              <InfoBox title="Tip" variant="tip">
                You can switch between multiple workspaces from the sidebar dropdown at the bottom of the left navigation.
              </InfoBox>
            </GuideSection>

            {/* 3. Creating Bots */}
            <GuideSection id="creating-bots" title="Creating AI Bots" icon={Bot}>
              <p>
                To create a new bot, click <strong>Create Agent</strong> from the Dashboard or Studio. You'll be guided 
                through a 4-step wizard:
              </p>
              <ol className="list-decimal pl-5 space-y-3 text-muted-foreground mt-4">
                <li><strong>Identity:</strong> Give your bot a name and description. Choose a language.</li>
                <li><strong>Behavior:</strong> Write a system prompt (e.g., "You are a helpful customer support agent"). Add optional output format instructions (e.g., "Always respond in JSON").</li>
                <li><strong>Knowledge:</strong> Select an embedding model and chunking strategy. Enable web search fallback if desired.</li>
                <li><strong>Model:</strong> Choose your LLM provider (Groq, OpenAI, or Ollama) and select a specific model. Enter your API key if required.</li>
              </ol>
            </GuideSection>

            {/* 4. AI Auto-Configure */}
            <GuideSection id="ai-auto-configure" title="AI Auto-Configure" icon={Sparkles}>
              <p>
                Don't want to manually write prompts? Use <strong>AI Auto-Configure</strong> on Step 1 of the wizard. Simply describe 
                your bot in one sentence, like:
              </p>
              <div className="bg-muted/30 border border-border/50 rounded-xl p-4 my-4 font-mono text-sm">
                "A customer support agent for an e-commerce store that responds in a friendly tone and outputs JSON"
              </div>
              <p>
                Our Meta-Agent will automatically generate a name, description, system prompt, and output format instructions for you. 
                You can always review and edit the generated configuration.
              </p>
            </GuideSection>

            {/* 5. Knowledge Base */}
            <GuideSection id="knowledge-base" title="Knowledge Base" icon={Database}>
              <p>
                The Knowledge Base is where your bot gets its intelligence. You can add knowledge in two ways:
              </p>
              <h4 className="font-bold mt-6 mb-2">Document Upload</h4>
              <ul className="list-disc pl-5 space-y-1 text-muted-foreground">
                <li>Navigate to the <strong>Knowledge</strong> page from the sidebar.</li>
                <li>Select an agent and click <strong>Upload Document</strong>.</li>
                <li>Supported formats: <strong>PDF, TXT, CSV</strong>.</li>
                <li>Documents are automatically chunked and embedded into a vector database.</li>
              </ul>
              <h4 className="font-bold mt-6 mb-2">Website URL Scraping</h4>
              <ul className="list-disc pl-5 space-y-1 text-muted-foreground">
                <li>Paste any public website URL in the <strong>Scrape Website</strong> input.</li>
                <li>We extract the text content, chunk it, and embed it — just like a document.</li>
              </ul>
              <h4 className="font-bold mt-6 mb-2">Configuration Options</h4>
              <ul className="list-disc pl-5 space-y-1 text-muted-foreground">
                <li><strong>Embedding Models:</strong> all-MiniLM-L6-v2 (default), nomic-embed, OpenAI embeddings.</li>
                <li><strong>Chunking Strategies:</strong> Sentence-based, paragraph-based, or fixed-size chunks.</li>
              </ul>
            </GuideSection>

            {/* 6. Studio */}
            <GuideSection id="studio" title="Agent Studio" icon={MessageSquare}>
              <p>
                The Studio is your testing ground. Here you can see all your bots, chat with them in real-time, 
                and verify that they're answering questions correctly based on their knowledge base.
              </p>
              <ul className="list-disc pl-5 space-y-1 text-muted-foreground mt-4">
                <li>Click on any bot card to open a chat session.</li>
                <li>View agent settings, update system prompts, and manage documents from here.</li>
                <li>Delete or reconfigure agents as needed.</li>
              </ul>
            </GuideSection>

            {/* 7. Agent Networks */}
            <GuideSection id="agent-networks" title="Agent Networks (Projects)" icon={Layers}>
              <p>
                Agent Networks let you group multiple bots into a <strong>Project</strong>. This is useful when you want 
                multiple specialized bots working together — for example, a Sales bot and a Support bot collaborating under 
                one umbrella.
              </p>
              <ul className="list-disc pl-5 space-y-1 text-muted-foreground mt-4">
                <li>Create a new project from the Studio page.</li>
                <li>Add sub-agents to a project from the project detail view.</li>
                <li>Configure shared API connections and global settings at the project level.</li>
              </ul>
            </GuideSection>

            {/* 8. Chat Widgets */}
            <GuideSection id="chat-widgets" title="Deploying Chat Widgets" icon={Globe}>
              <p>
                Turn any bot into a public-facing chat widget that you can embed on your website.
              </p>
              <ol className="list-decimal pl-5 space-y-2 text-muted-foreground mt-4">
                <li>Go to <strong>Chatbots</strong> in the sidebar and create a new chatbot linked to your agent.</li>
                <li>Open the <strong>Widget Editor</strong> to customize appearance: theme color, welcome message, position, avatar, border radius, and font.</li>
                <li>Configure security: add allowed domains and generate a Developer API Key.</li>
                <li>Copy the generated code snippet (HTML, React, or cURL) and paste it into your website.</li>
              </ol>
              <InfoBox title="Integration Options">
                <ul className="list-disc pl-5 space-y-1 text-sm">
                  <li><strong>HTML Script Tag:</strong> One line of code, works on any website.</li>
                  <li><strong>React Component:</strong> A drop-in component for React/Next.js apps.</li>
                  <li><strong>REST API (cURL):</strong> Server-side integration for custom backends.</li>
                </ul>
              </InfoBox>
            </GuideSection>

            {/* 9. Analytics */}
            <GuideSection id="analytics" title="Analytics & Monitoring" icon={BarChart3}>
              <p>
                The Analytics page gives you a high-level view of your platform's usage:
              </p>
              <ul className="list-disc pl-5 space-y-1 text-muted-foreground mt-4">
                <li><strong>Total Messages:</strong> Total queries processed across all agents.</li>
                <li><strong>Active Agents:</strong> Number of deployed bots.</li>
                <li><strong>Documents Indexed:</strong> Total documents in your knowledge base.</li>
                <li><strong>Response Time Charts:</strong> Visualize performance trends over time.</li>
              </ul>
            </GuideSection>

            {/* 10. Feedback */}
            <GuideSection id="feedback" title="Feedback & Corrections" icon={RefreshCw}>
              <p>
                BlinkBot features a unique <strong>feedback loop</strong> that makes your bots smarter over time:
              </p>
              <ol className="list-decimal pl-5 space-y-2 text-muted-foreground mt-4">
                <li>When a bot gives a wrong answer, users can <strong>flag it</strong> with a category (e.g., "Incorrect", "Outdated").</li>
                <li>Flagged messages appear in the <strong>Chat</strong> page as pending verifications.</li>
                <li>Admins can add correction comments. These corrections are automatically injected into the bot's context as a <strong>memory patch</strong>.</li>
                <li>The bot will avoid repeating the same mistake in future conversations.</li>
              </ol>
              <InfoBox title="How It Works" variant="tip">
                Memory patches are temporary corrections stored in the database. They are appended to the system prompt dynamically before each conversation, ensuring the bot learns from past mistakes without retraining.
              </InfoBox>
            </GuideSection>

            {/* 11. Billing */}
            <GuideSection id="billing" title="Billing & Plans" icon={CreditCard}>
              <p>
                BlinkBot offers three pre-defined plans and a fully customizable plan builder:
              </p>
              <div className="grid sm:grid-cols-3 gap-4 mt-6">
                <PlanCard name="Starter" price="$0" features={["1 Bot", "1K Messages", "100 MB"]} />
                <PlanCard name="Pro" price="$24/mo" features={["5 Bots", "10K Messages", "500 MB", "2 Widgets"]} highlight />
                <PlanCard name="Enterprise" price="$120/mo" features={["20 Bots", "100K Messages", "5 GB", "10 Widgets"]} />
              </div>
              <p className="mt-4">
                The <strong>Custom Plan Builder</strong> lets you use sliders to adjust the exact number of agents, messages, storage, and widgets you need — with dynamic pricing calculated in real-time.
              </p>
            </GuideSection>

            {/* 12. Languages */}
            <GuideSection id="languages" title="Multi-Language Support" icon={Globe}>
              <p>
                BlinkBot supports configuring your bots in multiple languages:
              </p>
              <div className="flex flex-wrap gap-2 mt-4">
                {["English", "Hindi", "Spanish", "French", "German", "Chinese", "Japanese", "Arabic"].map(lang => (
                  <span key={lang} className="px-3 py-1 bg-muted/50 border border-border/50 rounded-full text-sm font-medium">{lang}</span>
                ))}
              </div>
              <p className="mt-4 text-muted-foreground text-sm">
                The language setting affects how the bot structures its responses and can be changed at any time from the agent settings.
              </p>
            </GuideSection>

            {/* 13. FAQ */}
            <GuideSection id="faq" title="Troubleshooting & FAQs" icon={Search}>
              <div className="space-y-4">
                <FAQItem q="My bot says it doesn't know the answer?" a="Ensure your documents have finished processing in the Knowledge Base. If the answer isn't in the uploaded text, the bot is trained to decline rather than hallucinate. You can also enable Web Search Fallback to let the bot search the internet." />
                <FAQItem q="How do I upgrade my storage limits?" a="Visit the Billing page to upgrade your subscription tier or use the Custom Plan Builder for fine-grained control." />
                <FAQItem q="Can I use my own OpenAI or Groq API key?" a="Yes! When creating a bot, select your provider and enter your API key on Step 4 of the wizard. Your key is stored securely and used only for your bot's requests." />
                <FAQItem q="How do I embed the widget on my website?" a="Go to Chatbots → select your chatbot → Widget Editor → copy the HTML script tag and paste it before the closing </body> tag on your site." />
                <FAQItem q="Is my data secure?" a="Absolutely. Each workspace is isolated. Your documents are chunked, embedded, and stored in a private vector database. We never use your data to train public models." />
              </div>
            </GuideSection>
          </div>
        </main>
      </div>
    </div>
  );
}

/* ═══════════════════════ SUB-COMPONENTS ═══════════════════════ */

function GuideSection({ id, title, icon: Icon, children }) {
  return (
    <section id={id} className="scroll-mt-24 space-y-4">
      <h2 className="text-2xl font-bold flex items-center gap-3 border-b border-border/50 pb-3">
        <Icon size={22} className="text-primary" />
        {title}
      </h2>
      <div className="text-muted-foreground leading-relaxed space-y-3">
        {children}
      </div>
    </section>
  );
}

function InfoBox({ title, children, variant = "info" }) {
  const colors = variant === "tip" 
    ? "bg-emerald-500/5 border-emerald-500/20 text-emerald-700 dark:text-emerald-400"
    : "bg-primary/5 border-primary/20 text-primary";
  return (
    <div className={`mt-4 p-4 rounded-xl border ${colors}`}>
      <h4 className="text-sm font-bold mb-2">{title}</h4>
      <div className="text-foreground">{children}</div>
    </div>
  );
}

function PlanCard({ name, price, features, highlight }) {
  return (
    <div className={`p-4 rounded-xl border text-center ${highlight ? 'border-primary bg-primary/5' : 'border-border/50 bg-card'}`}>
      <h4 className="font-bold">{name}</h4>
      <p className="text-2xl font-extrabold my-2">{price}</p>
      <ul className="text-xs text-muted-foreground space-y-1">
        {features.map((f, i) => <li key={i}>{f}</li>)}
      </ul>
    </div>
  );
}

function FAQItem({ q, a }) {
  return (
    <div className="bg-card border border-border/50 p-5 rounded-xl">
      <h4 className="font-bold mb-2 text-foreground">{q}</h4>
      <p className="text-sm text-muted-foreground leading-relaxed">{a}</p>
    </div>
  );
}

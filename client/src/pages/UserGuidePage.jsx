import React from 'react';
import { Link } from 'react-router-dom';
import { ChevronLeft, BookOpen } from 'lucide-react';
import Logo from '../components/shared/Logo';
import { useUIStore } from '../store/useUIStore';

export default function UserGuidePage() {
  const darkMode = useUIStore((state) => state.darkMode);

  return (
    <div className="min-h-screen bg-background text-foreground font-sans">
      <nav className="flex items-center justify-between px-8 py-6 max-w-4xl mx-auto border-b border-border/50">
        <div className="flex items-center gap-4">
          <Link to="/" className="p-2 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-all">
            <ChevronLeft size={20} />
          </Link>
          <Logo />
        </div>
      </nav>

      <main className="max-w-4xl mx-auto px-8 py-12 pb-24">
        <div className="mb-12">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
              <BookOpen className="text-primary" size={20} />
            </div>
            <h1 className="text-4xl font-extrabold tracking-tight">User Guide</h1>
          </div>
          <p className="text-muted-foreground text-lg">Everything you need to know to build custom AI agents on your data.</p>
        </div>

        <div className="space-y-12">
          <section className="space-y-4">
            <h2 className="text-2xl font-bold border-b border-border/50 pb-2">1. Introduction</h2>
            <p className="text-muted-foreground leading-relaxed">
              Welcome to RAGMate! We provide a powerful, secure AI operating system that allows you to instantly spin up intelligent agents equipped with your business's proprietary knowledge. 
              By connecting your internal documents or websites, your custom AI agents can answer questions accurately without hallucinating.
            </p>
          </section>

          <section className="space-y-4">
            <h2 className="text-2xl font-bold border-b border-border/50 pb-2">2. Account Setup & Workspaces</h2>
            <p className="text-muted-foreground leading-relaxed">
              Once you create an account, you will be placed into a <strong>Workspace</strong>. A workspace is a secure silo for your team. You can invite your colleagues to your workspace via the Team page.
              All documents, agents, and chatbots created within a workspace are isolated and secure.
            </p>
          </section>

          <section className="space-y-4">
            <h2 className="text-2xl font-bold border-b border-border/50 pb-2">3. Creating an AI Agent</h2>
            <ul className="list-decimal pl-6 space-y-2 text-muted-foreground">
              <li>Navigate to the Dashboard and click <strong>Create Agent</strong>.</li>
              <li>Provide a name, description, and an initial system prompt (e.g., "You are a helpful customer support bot").</li>
              <li>Choose your preferred Language Model (e.g., GPT-4 or Llama 3) using your own API keys.</li>
              <li>Save your agent. You can always update its settings later.</li>
            </ul>
          </section>

          <section className="space-y-4">
            <h2 className="text-2xl font-bold border-b border-border/50 pb-2">4. Adding Knowledge (Documents)</h2>
            <p className="text-muted-foreground leading-relaxed">
              An agent is only as smart as the data it has access to. To teach your agent:
            </p>
            <ul className="list-disc pl-6 space-y-2 text-muted-foreground">
              <li>Go to the <strong>Knowledge Base</strong> tab within your agent's dashboard.</li>
              <li>Click <strong>Upload Document</strong> to add PDFs, TXT, or CSV files.</li>
              <li>Our engine will automatically chunk and embed the text into a secure vector database.</li>
              <li>Once processed, the agent will instantly use this data to answer questions!</li>
            </ul>
          </section>

          <section className="space-y-4">
            <h2 className="text-2xl font-bold border-b border-border/50 pb-2">5. Deploying the Chat Widget</h2>
            <p className="text-muted-foreground leading-relaxed">
              Ready to deploy your agent to your website? 
            </p>
            <ul className="list-disc pl-6 space-y-2 text-muted-foreground">
              <li>Go to the <strong>Chat Widget</strong> tab.</li>
              <li>Customize the widget's appearance (colors, welcome message, positioning).</li>
              <li>Copy the generated <code>&lt;script&gt;</code> tag and paste it into your website's HTML right before the closing <code>&lt;/body&gt;</code> tag.</li>
              <li>Your widget is now live and tracking analytics!</li>
            </ul>
          </section>

          <section className="space-y-4">
            <h2 className="text-2xl font-bold border-b border-border/50 pb-2">6. Troubleshooting & FAQs</h2>
            <div className="space-y-4">
              <div className="bg-card border border-border/50 p-4 rounded-xl">
                <h4 className="font-bold mb-1">My agent says it doesn't know the answer?</h4>
                <p className="text-sm text-muted-foreground">Ensure your documents have finished processing in the Knowledge Base. If the answer isn't explicitly in the uploaded text, the agent is trained to decline rather than hallucinate.</p>
              </div>
              <div className="bg-card border border-border/50 p-4 rounded-xl">
                <h4 className="font-bold mb-1">How do I upgrade my storage limits?</h4>
                <p className="text-sm text-muted-foreground">Visit the Billing page to upgrade your subscription tier for increased document storage and widget message limits.</p>
              </div>
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}

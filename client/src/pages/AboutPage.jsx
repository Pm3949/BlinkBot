import { Link } from 'react-router-dom';
import { usePageSeo } from '../hooks/usePageSeo';
import { ChevronLeft, Heart, Zap, Shield, Globe, Users, Bot } from 'lucide-react';
import Logo from '../components/shared/Logo';

export default function AboutPage() {
  usePageSeo('About Us', 'Learn about BlinkBot — our mission to help every business build custom AI bots powered by their own data, without needing any code.');
  return (
    <div className="min-h-screen bg-background text-foreground font-sans">
      <nav className="flex items-center justify-between px-6 md:px-8 py-6 max-w-4xl mx-auto border-b border-border/50">
        <div className="flex items-center gap-4">
          <Link to="/" className="p-2 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-all">
            <ChevronLeft size={20} />
          </Link>
          <Logo />
        </div>
      </nav>

      <main className="max-w-4xl mx-auto px-6 md:px-8 py-12 pb-24">
        {/* Header */}
        <div className="mb-16 text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-bold uppercase tracking-wider mb-4">
            <Heart size={14} /> About Us
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight">We're building the future of custom AI.</h1>
          <p className="text-lg text-muted-foreground mt-4 max-w-2xl mx-auto leading-relaxed">
            BlinkBot is an AI bot platform that lets businesses and developers create, train, and deploy intelligent conversational agents — all powered by their own proprietary data.
          </p>
        </div>

        {/* Mission */}
        <section className="mb-16">
          <div className="bg-gradient-to-br from-primary/5 to-purple-500/5 border border-border/50 rounded-[24px] p-8 md:p-10">
            <h2 className="text-2xl font-bold mb-4 flex items-center gap-3">
              <Zap className="text-primary" size={24} /> Our Mission
            </h2>
            <p className="text-muted-foreground leading-relaxed text-lg">
              We believe every business deserves an AI that actually understands their world — not a generic chatbot that hallucinates answers. 
              BlinkBot makes it effortless to build custom AI bots that are grounded in your real documents, trained on your real data, 
              and deployed exactly where your customers need them.
            </p>
          </div>
        </section>

        {/* Values */}
        <section className="mb-16">
          <h2 className="text-2xl font-bold mb-8 text-center">What We Stand For</h2>
          <div className="grid md:grid-cols-2 gap-6">
            <ValueCard 
              icon={Shield} 
              title="Privacy First" 
              desc="Your data is never used to train public models. We process, embed, and store your documents in isolated, secure workspaces."
            />
            <ValueCard 
              icon={Zap} 
              title="Speed & Simplicity" 
              desc="Go from zero to a fully deployed AI bot in under 5 minutes. No machine learning expertise required."
            />
            <ValueCard 
              icon={Globe} 
              title="Open & Flexible" 
              desc="We support multiple LLM providers (Groq, OpenAI, Ollama) and never lock you into a single ecosystem."
            />
            <ValueCard 
              icon={Users} 
              title="Built for Teams" 
              desc="Multi-workspace, role-based access, team invites — BlinkBot scales with your organization from day one."
            />
          </div>
        </section>

        {/* What we offer */}
        <section className="mb-16">
          <h2 className="text-2xl font-bold mb-8 text-center">What BlinkBot Offers</h2>
          <div className="space-y-4">
            {[
              { icon: Bot, text: "Custom AI bots built on your documents, with a 4-step guided wizard" },
              { icon: Zap, text: "AI Auto-Configure — describe your bot in one sentence, we do the rest" },
              { icon: Globe, text: "Embeddable chat widgets for your website (HTML, React, REST API)" },
              { icon: Shield, text: "Self-learning feedback loops — bots improve from user corrections" },
              { icon: Users, text: "Team collaboration with multi-workspace support and role management" },
            ].map((item, i) => (
              <div key={i} className="flex items-center gap-4 p-4 rounded-xl border border-border/50 bg-card hover:bg-muted/30 transition-all">
                <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center shrink-0">
                  <item.icon size={20} className="text-primary" />
                </div>
                <p className="text-sm font-medium">{item.text}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Contact */}
        <section className="text-center bg-card border border-border/50 rounded-[24px] p-8 md:p-10">
          <h2 className="text-2xl font-bold mb-3">Get in Touch</h2>
          <p className="text-muted-foreground mb-6">Have questions, partnership ideas, or feedback? We'd love to hear from you.</p>
          <a href="mailto:techmate.ed@gmail.com" className="btn-primary px-8 py-3 rounded-full font-bold text-sm inline-flex items-center gap-2 shadow-lg shadow-primary/20 hover:shadow-primary/40 transition-all">
            Contact Us
          </a>
          <p className="text-xs text-muted-foreground mt-4">techmate.ed@gmail.com</p>
        </section>
      </main>
    </div>
  );
}

function ValueCard({ icon: Icon, title, desc }) {
  return (
    <div className="bg-card border border-border/50 rounded-[20px] p-6 hover:border-primary/30 transition-all">
      <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center mb-4">
        <Icon size={20} className="text-primary" />
      </div>
      <h3 className="font-bold mb-2">{title}</h3>
      <p className="text-sm text-muted-foreground leading-relaxed">{desc}</p>
    </div>
  );
}

import { Link } from 'react-router-dom';
import { usePageSeo } from '../hooks/usePageSeo';
import { ChevronLeft, Heart, Zap, Shield, Globe, Users, Bot } from 'lucide-react';
import Logo from '../components/shared/Logo';

export default function AboutPage() {
  usePageSeo('About Us', 'Learn about BlinkBot, and our mission to help every business build secure, zero-code AI agent teams powered by their own data and tools.');
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
          <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight">We're building the future of secure AI automation.</h1>
          <p className="text-lg text-muted-foreground mt-4 max-w-2xl mx-auto leading-relaxed">
            BlinkBot is a zero-code AI agent platform that lets businesses create, deploy, and manage intelligent agent teams, equipped with tools and grounded securely in company data.
          </p>
        </div>

        {/* Mission */}
        <section className="mb-16">
          <div className="bg-gradient-to-br from-primary/5 to-purple-500/5 border border-border/50 rounded-[24px] p-8 md:p-10">
            <h2 className="text-2xl font-bold mb-4 flex items-center gap-3">
              <Zap className="text-primary" size={24} /> Our Mission
            </h2>
            <p className="text-muted-foreground leading-relaxed text-lg">
              We believe automation shouldn't require complex code or compromise security. BlinkBot makes it effortless to build intelligent, multi-agent teams from a single prompt, connect them to your tools like WhatsApp and SMS, and secure them with built-in human verification.
            </p>
          </div>
        </section>

        {/* Values */}
        <section className="mb-16">
          <h2 className="text-2xl font-bold mb-8 text-center">What We Stand For</h2>
          <div className="grid md:grid-cols-2 gap-6">
            <ValueCard 
              icon={Shield} 
              title="Human-in-Control" 
              desc="Safety first. Agents running critical workflows can be set to pause and request manual human approval before execution."
            />
            <ValueCard 
              icon={Zap} 
              title="Zero-Code Simplicity" 
              desc="Describe your workflow in a single prompt and watch a fully-routed, tool-equipped agent team spin up instantly."
            />
            <ValueCard 
              icon={Globe} 
              title="Omnichannel & Connected" 
              desc="We integrate seamlessly with user-facing channels like WhatsApp, SMS, and custom API webhooks."
            />
            <ValueCard 
              icon={Users} 
              title="Enterprise Security" 
              desc="PostgreSQL Row-Level Security keeps workspaces completely isolated, protecting your private company documents."
            />
          </div>
        </section>

        {/* What we offer */}
        <section className="mb-16">
          <h2 className="text-2xl font-bold mb-8 text-center">What BlinkBot Offers</h2>
          <div className="space-y-4">
            {[
              { icon: Bot, text: "Zero-code creation of specialized agent teams using a single prompt" },
              { icon: Zap, text: "Automated integrations for WhatsApp, SMS, and custom API endpoints" },
              { icon: Shield, text: "Human-in-the-Loop approvals for sensitive actions" },
              { icon: Globe, text: "Embeddable website chat widgets (1-line script tags)" },
              { icon: Users, text: "Private workspaces with role-based access control (RBAC)" },
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
          <a href="mailto:blinkbot07@gmail.com" className="btn-primary px-8 py-3 rounded-full font-bold text-sm inline-flex items-center gap-2 shadow-lg shadow-primary/20 hover:shadow-primary/40 transition-all">
            Contact Us
          </a>
          <p className="text-xs text-muted-foreground mt-4">blinkbot07@gmail.com</p>
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

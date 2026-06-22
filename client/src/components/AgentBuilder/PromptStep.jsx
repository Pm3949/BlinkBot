import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Sparkles, ArrowRight, Lightbulb, Zap, ShoppingBag, Headset, Wand2 } from 'lucide-react';

const SUGGESTIONS = [
  {
    icon: ShoppingBag,
    label: "E-commerce Support",
    prompt: "I need an e-commerce bot to track orders via my API, handle returns, and suggest products based on my catalog."
  },
  {
    icon: Headset,
    label: "IT Helpdesk",
    prompt: "Create an internal IT support network. One agent handles password resets, another searches knowledge base for troubleshooting."
  },
  {
    icon: Zap,
    label: "Financial Analyst",
    prompt: "A network of financial agents. One agent fetches real-time stock data, another summarizes financial reports from PDFs."
  }
];

export default function PromptStep({ onSubmit }) {
  const [prompt, setPrompt] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (prompt.trim()) {
      onSubmit(prompt);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="max-w-4xl mx-auto mt-8 px-4"
    >
      <div className="text-center mb-10">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: "spring", stiffness: 260, damping: 20 }}
          className="inline-flex items-center justify-center p-4 bg-primary/15 rounded-2xl mb-6 shadow-sm border border-primary/25 ring-1 ring-primary/10"
        >
          <Wand2 className="w-8 h-8 text-primary" />
        </motion.div>
        <h1 className="text-4xl md:text-5xl font-extrabold text-foreground tracking-tight mb-4">
          Design Your{" "}
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary to-orange-400">
            Agent Network
          </span>
        </h1>
        <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
          Describe your ideal AI workforce, and our Master Builder will architect the perfect multi-agent blueprint.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="relative group max-w-3xl mx-auto">
        {/* Glow border */}
        <div className="absolute -inset-0.5 bg-gradient-to-r from-primary/50 via-orange-500/30 to-primary/50 rounded-3xl blur-lg opacity-40 group-hover:opacity-70 transition duration-700" />
        
        <div className="relative bg-card border border-border rounded-2xl shadow-xl overflow-hidden flex flex-col backdrop-blur-md">
          <div className="p-6 md:p-8">
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="e.g., I need a customer service gateway that routes to a Sales Agent for pricing and a Tech Support Agent for troubleshooting..."
              className="w-full h-40 md:h-48 text-base border-0 focus:ring-0 resize-none text-foreground bg-transparent placeholder-muted-foreground outline-none leading-relaxed"
              autoFocus
            />
          </div>

          <div className="bg-muted/40 px-6 md:px-8 py-4 border-t border-border flex flex-col sm:flex-row justify-between items-center gap-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground font-medium">
              <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
              Powered by LLM Orchestration
            </div>
            <button
              type="submit"
              disabled={!prompt.trim()}
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-8 py-3 btn-primary text-white rounded-xl font-semibold transition-all shadow-lg shadow-primary/25 hover:-translate-y-0.5 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:translate-y-0"
            >
              Generate Blueprint
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </form>

      {/* Suggestions */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
        className="mt-12 max-w-3xl mx-auto"
      >
        <div className="flex items-center gap-2 mb-5 text-xs font-semibold text-muted-foreground uppercase tracking-widest justify-center">
          <Lightbulb className="w-3.5 h-3.5" />
          <span>Try these templates</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {SUGGESTIONS.map((suggestion, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => setPrompt(suggestion.prompt)}
              className="flex flex-col items-start p-5 text-left glass-card rounded-2xl hover:border-primary/40 transition-all group"
            >
              <div className="flex items-center gap-3 mb-3">
                <div className="p-2.5 bg-primary/10 rounded-xl group-hover:bg-primary/20 transition-colors border border-primary/20">
                  <suggestion.icon className="w-4 h-4 text-primary" />
                </div>
                <span className="font-semibold text-foreground text-sm">
                  {suggestion.label}
                </span>
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed group-hover:text-foreground transition-colors">
                {suggestion.prompt}
              </p>
            </button>
          ))}
        </div>
      </motion.div>
    </motion.div>
  );
}

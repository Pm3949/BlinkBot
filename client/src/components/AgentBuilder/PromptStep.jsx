import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Sparkles, ArrowRight, Lightbulb, Zap, ShoppingBag, Headset } from 'lucide-react';

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
      className="max-w-4xl mx-auto mt-12 px-4"
    >
      <div className="text-center mb-10">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: "spring", stiffness: 260, damping: 20 }}
          className="inline-flex items-center justify-center p-4 bg-purple-500/10 rounded-2xl mb-6 shadow-sm border border-purple-500/20"
        >
          <Sparkles className="w-8 h-8 text-purple-400" />
        </motion.div>
        <h1 className="text-5xl md:text-6xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-slate-100 via-purple-300 to-slate-100 tracking-tight mb-6">
          Design Your Agent Network
        </h1>
        <p className="text-xl text-slate-400 max-w-2xl mx-auto">
          Describe your ideal AI workforce, and our Master Builder will architect the perfect multi-agent blueprint.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="relative group max-w-3xl mx-auto">
        <div className="absolute -inset-1 bg-gradient-to-r from-purple-600/40 via-indigo-600/40 to-blue-600/40 rounded-[2rem] blur-xl opacity-50 group-hover:opacity-70 transition duration-1000 group-hover:duration-300"></div>
        <div className="relative bg-slate-900/80 backdrop-blur-xl rounded-[2rem] shadow-2xl border border-slate-700/50 overflow-hidden flex flex-col">
          <div className="p-6 md:p-8">
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="e.g., I need a customer service gateway that routes to a Sales Agent for pricing and a Tech Support Agent for troubleshooting..."
              className="w-full h-40 md:h-48 text-xl border-0 focus:ring-0 resize-none text-slate-200 bg-transparent placeholder-slate-500 outline-none"
              autoFocus
            />
          </div>
          
          <div className="bg-slate-950/50 backdrop-blur-md px-6 md:px-8 py-5 border-t border-slate-800 flex flex-col sm:flex-row justify-between items-center gap-4">
            <div className="flex items-center gap-2 text-sm text-slate-400 font-medium">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              Powered by LLM Orchestration
            </div>
            <button
              type="submit"
              disabled={!prompt.trim()}
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-8 py-3.5 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl font-semibold transition-all shadow-lg hover:shadow-purple-500/25 hover:-translate-y-0.5 border border-purple-500/30"
            >
              Generate Blueprint
              <ArrowRight className="w-5 h-5" />
            </button>
          </div>
        </div>
      </form>

      {/* Suggestions Section */}
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
        className="mt-16 max-w-3xl mx-auto"
      >
        <div className="flex items-center gap-3 mb-6 text-sm font-semibold text-slate-400 uppercase tracking-wider justify-center">
          <Lightbulb className="w-4 h-4" />
          <span>Try these templates</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {SUGGESTIONS.map((suggestion, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => setPrompt(suggestion.prompt)}
              className="flex flex-col items-start p-5 text-left bg-slate-900/50 rounded-2xl border border-slate-800 shadow-sm hover:shadow-lg hover:border-purple-500/50 hover:bg-slate-800/80 transition-all group"
            >
              <div className="flex items-center gap-3 mb-3">
                <div className="p-2.5 bg-slate-800 rounded-xl group-hover:bg-purple-500/20 group-hover:text-purple-400 transition-colors border border-slate-700 group-hover:border-purple-500/30">
                  <suggestion.icon className="w-5 h-5 text-slate-400 group-hover:text-purple-400" />
                </div>
                <span className="font-semibold text-slate-200 group-hover:text-purple-300 transition-colors">
                  {suggestion.label}
                </span>
              </div>
              <p className="text-sm text-slate-400 leading-relaxed group-hover:text-slate-300">
                {suggestion.prompt}
              </p>
            </button>
          ))}
        </div>
      </motion.div>
    </motion.div>
  );
}

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Sparkles, ArrowRight } from 'lucide-react';

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
      className="max-w-3xl mx-auto mt-20"
    >
      <div className="text-center mb-10">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: "spring", stiffness: 260, damping: 20 }}
          className="inline-flex items-center justify-center p-3 bg-purple-100 rounded-full mb-6"
        >
          <Sparkles className="w-8 h-8 text-purple-600" />
        </motion.div>
        <h1 className="text-5xl font-extrabold text-gray-900 tracking-tight mb-4">
          What kind of agent do you need?
        </h1>
        <p className="text-xl text-gray-500">
          Describe your ideal AI agent network, and our Master Builder will generate the perfect blueprint.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="relative group">
        <div className="absolute -inset-1 bg-gradient-to-r from-purple-600 to-blue-600 rounded-2xl blur opacity-25 group-hover:opacity-50 transition duration-1000 group-hover:duration-200"></div>
        <div className="relative bg-white rounded-2xl shadow-xl overflow-hidden flex flex-col">
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="e.g., I need an e-commerce bot to track orders via my API and suggest products based on my catalog..."
            className="w-full h-48 p-6 text-lg border-0 focus:ring-0 resize-none text-gray-700 bg-transparent placeholder-gray-400"
            autoFocus
          />
          <div className="bg-gray-50 px-6 py-4 border-t flex justify-between items-center">
            <span className="text-sm text-gray-500">Powered by Gemini 2.5 Flash</span>
            <button
              type="submit"
              disabled={!prompt.trim()}
              className="inline-flex items-center gap-2 px-6 py-3 bg-gray-900 hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl font-semibold transition-colors"
            >
              Generate Blueprint
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </form>
    </motion.div>
  );
}

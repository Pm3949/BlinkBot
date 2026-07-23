import React, { useState, useEffect, useMemo } from 'react';
import { useTraceStore } from '../../store/useTraceStore';
import { Search, ShieldAlert, Sparkles, Terminal, Activity, X } from 'lucide-react';

export default function TracePanel({ onClose }) {
  const { steps, clearSteps, isRawMode, setRawMode } = useTraceStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');

  // Debounce search query
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedQuery(searchQuery);
    }, 300);
    return () => clearTimeout(handler);
  }, [searchQuery]);

  // Helper to escape regex special characters
  const escapeRegExp = (string) => {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  };

  // Helper function to highlight text matching query
  const highlightText = (text, query) => {
    if (!query) return text;
    const parts = text.split(new RegExp(`(${escapeRegExp(query)})`, 'gi'));
    return (
      <>
        {parts.map((part, index) => 
          part.toLowerCase() === query.toLowerCase() ? (
            <mark key={index} className="bg-yellow-500/40 text-yellow-200 rounded px-0.5">
              {part}
            </mark>
          ) : (
            part
          )
        )}
      </>
    );
  };

  // Filtered steps based on search
  const filteredSteps = useMemo(() => {
    if (!debouncedQuery) return steps;
    const query = debouncedQuery.toLowerCase();
    return steps.filter(step => 
      (step.agentName && step.agentName.toLowerCase().includes(query)) ||
      (step.action && step.action.toLowerCase().includes(query)) ||
      (step.payload && JSON.stringify(step.payload).toLowerCase().includes(query)) ||
      (step.logs && step.logs.toLowerCase().includes(query))
    );
  }, [steps, debouncedQuery]);

  return (
    <div className="flex flex-col h-full bg-card/95 backdrop-blur-md border-l border-border/50 shadow-2xl relative z-10 w-[450px]">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-border/50 bg-background/50">
        <div>
          <h2 className="text-lg font-semibold bg-gradient-to-r from-purple-400 to-indigo-400 bg-clip-text text-transparent flex items-center gap-2">
            <Terminal size={18} /> Execution Trace
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">Real-time agent execution pipeline</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={clearSteps}
            className="text-xs font-semibold px-2.5 py-1.5 rounded-lg bg-muted hover:bg-muted/80 text-muted-foreground hover:text-foreground transition-colors"
            title="Clear Logs"
          >
            Clear
          </button>
          {onClose && (
            <button
              onClick={onClose}
              className="text-muted-foreground hover:text-foreground transition-colors p-2 rounded-full hover:bg-muted/50"
              title="Close Panel"
            >
              <X size={20} />
            </button>
          )}
        </div>
      </div>

      {/* Control Area: Search & Toggles */}
      <div className="p-4 border-b border-border/50 bg-background/30 space-y-3">
        {/* Friendly vs Raw Mode Toggle */}
        <div className="flex items-center justify-between bg-muted/40 p-2 rounded-xl border border-border/50">
          <span className="text-xs font-medium text-muted-foreground">Log Format Mode</span>
          <div className="flex gap-1">
            <button
              onClick={() => setRawMode(false)}
              className={`text-xs px-3 py-1 rounded-lg font-semibold transition ${!isRawMode ? 'bg-primary text-primary-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'}`}
            >
              Friendly
            </button>
            <button
              onClick={() => setRawMode(true)}
              className={`text-xs px-3 py-1 rounded-lg font-semibold transition ${isRawMode ? 'bg-primary text-primary-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'}`}
            >
              Raw JSON
            </button>
          </div>
        </div>

        {/* Search Input */}
        <div className="relative">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search logs & payloads..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-background/50 border border-border/50 rounded-xl text-xs placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-purple-500/50"
          />
        </div>
      </div>

      {/* Steps List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {filteredSteps.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center text-muted-foreground opacity-70">
            <div className="w-12 h-12 rounded-full bg-purple-500/10 flex items-center justify-center mb-3">
              <Activity size={20} className="text-purple-400" />
            </div>
            <p className="text-xs">No trace steps captured yet.<br/>Interact in the chat to see agent traces.</p>
          </div>
        ) : (
          filteredSteps.map((step) => (
            <div key={step.id} className="border border-border/40 rounded-xl p-3 bg-muted/20 space-y-2.5 transition duration-300 hover:border-purple-500/30">
              {/* Step Header */}
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-1.5 font-bold text-foreground">
                  {step.type === 'routing' && <Sparkles size={13} className="text-purple-400" />}
                  {step.type === 'tool' && <Terminal size={13} className="text-emerald-400" />}
                  {step.type === 'error' && <ShieldAlert size={13} className="text-red-400" />}
                  <span>{highlightText(step.agentName || 'Agent Network', searchQuery)}</span>
                </div>
                <span className="text-[10px] text-muted-foreground font-mono">{step.timestamp}</span>
              </div>

              {/* Step Action / Detail */}
              <div className="text-xs text-muted-foreground leading-relaxed">
                <div className="font-semibold text-foreground/80 mb-1">
                  Action: {highlightText(step.action || 'invoked', searchQuery)}
                </div>
                {step.latency && (
                  <span className="inline-block px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-400 text-[10px] font-semibold mb-1">
                    Latency: {step.latency}ms
                  </span>
                )}
              </div>

              {/* Step Output/Payload Display based on raw/friendly mode */}
              <div className="text-xs font-mono bg-background/50 border border-border/30 rounded-lg p-2 overflow-x-auto max-h-48 scrollbar-thin">
                {isRawMode ? (
                  <pre className="text-[10px] text-purple-300 whitespace-pre-wrap">
                    {highlightText(JSON.stringify(step.payload || {}, null, 2), searchQuery)}
                  </pre>
                ) : (
                  <div className="text-[11px] text-foreground/90 whitespace-pre-wrap leading-relaxed">
                    {highlightText(step.logs || 'Step completed cleanly.', searchQuery)}
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

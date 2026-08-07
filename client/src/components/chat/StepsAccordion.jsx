import { useState, useEffect } from "react";
import {
  Brain,
  GitBranch,
  Bot,
  Terminal,
  CheckCircle2,
  FileText,
  ChevronDown,
  ChevronUp,
  Loader2,
  Zap,
} from "lucide-react";

const STEP_CONFIG = {
  thinking:   { icon: Brain,        color: "text-violet-400",  bg: "bg-violet-500/10" },
  routing:    { icon: GitBranch,    color: "text-blue-400",    bg: "bg-blue-500/10"   },
  generating: { icon: Bot,          color: "text-emerald-400", bg: "bg-emerald-500/10"},
  tool_call:  { icon: Terminal,     color: "text-amber-400",   bg: "bg-amber-500/10"  },
  tool_done:  { icon: CheckCircle2, color: "text-emerald-400", bg: "bg-emerald-500/10"},
  formatting: { icon: FileText,     color: "text-sky-400",     bg: "bg-sky-500/10"    },
};

function getConfig(status) {
  if (status.startsWith("tool_call_")) return STEP_CONFIG.tool_call;
  if (status.startsWith("tool_done_")) return STEP_CONFIG.tool_done;
  return STEP_CONFIG[status] || STEP_CONFIG.generating;
}

function StepRow({ step }) {
  const cfg = getConfig(step.status);
  const Icon = cfg.icon;
  const isActive = !step.done;

  return (
    <div className={`flex items-center gap-2.5 px-3 py-2 rounded-lg transition-all duration-300 ${cfg.bg} border border-white/5`}>
      <div className={`flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center ${cfg.bg}`}>
        {isActive ? (
          <Loader2 size={13} className={`${cfg.color} animate-spin`} />
        ) : (
          <Icon size={13} className={cfg.color} />
        )}
      </div>
      <span className={`text-xs font-medium ${isActive ? "text-foreground" : "text-muted-foreground"}`}>
        {step.label}
      </span>
      {step.done && (
        <CheckCircle2 size={12} className="ml-auto text-emerald-500 flex-shrink-0" />
      )}
    </div>
  );
}

export default function StepsAccordion({ steps = [], isStreaming = false }) {
  // For historical messages (all steps already done), start expanded.
  // For live streaming, start expanded and auto-collapse when done.
  const allAlreadyDone = steps.length > 0 && steps.every(s => s.done);
  const [isOpen, setIsOpen] = useState(allAlreadyDone ? false : true);

  useEffect(() => {
    if (isStreaming) {
      setIsOpen(true);
    } else if (steps.length > 0 && steps.every(s => s.done)) {
      // Small delay so the user sees the final checkmarks before collapsing
      const t = setTimeout(() => setIsOpen(false), 1200);
      return () => clearTimeout(t);
    }
  }, [isStreaming, steps]);

  if (!steps || steps.length === 0) return null;

  const doneCount = steps.filter(s => s.done).length;
  const total = steps.length;
  const allDone = doneCount === total && total > 0;

  return (
    <div className="mb-3 rounded-xl border border-white/8 bg-muted/20 overflow-hidden backdrop-blur-sm">
      {/* Header / pill */}
      <button
        onClick={() => setIsOpen(o => !o)}
        className="w-full flex items-center justify-between gap-2 px-3 py-2 hover:bg-white/5 transition-colors group"
      >
        <div className="flex items-center gap-2">
          <Zap size={13} className={allDone ? "text-emerald-400" : "text-violet-400 animate-pulse"} />
          <span className="text-xs font-semibold text-muted-foreground group-hover:text-foreground transition-colors">
            {allDone
              ? `${total} steps completed`
              : `${doneCount} / ${total} steps`}
          </span>
          {isStreaming && !allDone && (
            <Loader2 size={11} className="text-violet-400 animate-spin" />
          )}
        </div>
        {isOpen
          ? <ChevronUp size={13} className="text-muted-foreground" />
          : <ChevronDown size={13} className="text-muted-foreground" />
        }
      </button>

      {/* Steps list */}
      {isOpen && (
        <div className="flex flex-col gap-1 px-2 pb-2">
          {steps.map((step, i) => (
            <StepRow key={`${step.status}-${i}`} step={step} />
          ))}
        </div>
      )}
    </div>
  );
}

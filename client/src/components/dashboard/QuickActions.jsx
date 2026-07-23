import { motion } from "framer-motion";
import { UploadCloud, MessageSquare, Bot, FlaskConical, Globe, ArrowUpRight } from "lucide-react";
import { useNavigate } from "react-router-dom";

const actions = [
  {
    icon: FlaskConical,
    label: "Open Studio",
    description: "Build & configure agents",
    path: "/studio",
    color: "#FF4D00",
    bg: "rgba(255,77,0,0.08)",
    hoverBg: "rgba(255,77,0,0.14)",
  },
  {
    icon: MessageSquare,
    label: "Start Chat",
    description: "Talk to your agents live",
    path: "/chat",
    color: "#8b5cf6",
    bg: "rgba(139,92,246,0.08)",
    hoverBg: "rgba(139,92,246,0.14)",
  },
  {
    icon: Globe,
    label: "Manage Chatbots",
    description: "Deploy & embed widgets",
    path: "/chatbots",
    color: "#06b6d4",
    bg: "rgba(6,182,212,0.08)",
    hoverBg: "rgba(6,182,212,0.14)",
  },
];

export default function QuickActions({ onCreateAgent }) {
  const navigate = useNavigate();

  return (
    <div
      className="rounded-3xl border border-border/60 bg-card p-6"
      style={{ boxShadow: "0 2px 12px rgba(0,0,0,0.04)" }}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div>
          <h3 className="font-bold text-base text-foreground">Quick Actions</h3>
          <p className="text-xs text-muted-foreground mt-0.5">Jump to frequent workflows</p>
        </div>
        <span className="text-[10px] font-bold uppercase tracking-widest px-2.5 py-1 rounded-full bg-primary/8 text-primary" style={{ background: "rgba(255,77,0,0.08)" }}>
          Shortcuts
        </span>
      </div>

      {/* Create Agent — primary CTA */}
      <motion.button
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        onClick={onCreateAgent}
        className="w-full mb-3 relative overflow-hidden flex items-center gap-3 px-4 py-3.5 rounded-2xl text-white font-semibold text-sm transition-all"
        style={{ background: "linear-gradient(135deg, #FF4D00 0%, #ff7a3d 100%)", boxShadow: "0 4px 20px rgba(255,77,0,0.3)" }}
      >
        <div className="absolute inset-0 bg-white/0 hover:bg-white/5 transition-colors rounded-2xl" />
        <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-white/20 shrink-0">
          <Bot size={16} />
        </div>
        <div className="text-left">
          <div>Create New Agent</div>
          <div className="text-[11px] font-normal opacity-75 mt-0.5">AI-powered with RAG</div>
        </div>
        <ArrowUpRight size={14} className="ml-auto opacity-70" />
      </motion.button>

      {/* Other shortcuts */}
      <div className="space-y-2">
        {actions.map((action, i) => (
          <motion.button
            key={action.label}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.07 + 0.1 }}
            whileHover={{ x: 3 }}
            onClick={() => navigate(action.path)}
            className="w-full flex items-center gap-3 px-3.5 py-3 rounded-2xl border border-border/50 hover:border-border transition-all text-left group"
            style={{ background: action.bg }}
          >
            <div
              className="flex h-8 w-8 items-center justify-center rounded-xl shrink-0 group-hover:scale-105 transition-transform"
              style={{ background: action.hoverBg }}
            >
              <action.icon size={15} style={{ color: action.color }} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-semibold text-foreground">{action.label}</div>
              <div className="text-[11px] text-muted-foreground">{action.description}</div>
            </div>
            <ArrowUpRight
              size={13}
              className="shrink-0 opacity-0 group-hover:opacity-60 transition-all group-hover:translate-x-0.5 group-hover:-translate-y-0.5"
              style={{ color: action.color }}
            />
          </motion.button>
        ))}
      </div>
    </div>
  );
}

import { motion, AnimatePresence } from "framer-motion";
import { Bot, MessageSquare, BookOpen, Clock, Zap } from "lucide-react";

function formatDate(value) {
  if (!value) return "Recently";
  const date = new Date(value);
  const now = new Date();
  const diff = Math.floor((now - date) / 1000);
  if (diff < 60) return "Just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return new Intl.DateTimeFormat("en", { month: "short", day: "numeric" }).format(date);
}

const iconMap = {
  agent: { icon: Bot, color: "#FF4D00", bg: "rgba(255,77,0,0.1)", label: "Agent" },
  session: { icon: MessageSquare, color: "#8b5cf6", bg: "rgba(139,92,246,0.1)", label: "Chat" },
  note: { icon: BookOpen, color: "#06b6d4", bg: "rgba(6,182,212,0.1)", label: "Note" },
};

export default function ActivityFeed({ agents = [], sessions = [], notes = [] }) {
  const activity = [
    ...agents.slice(0, 3).map((a) => ({
      id: `agent-${a.id}`,
      type: "agent",
      title: a.name,
      subtitle: "Agent created",
      meta: formatDate(a.created_at),
    })),
    ...sessions.slice(0, 3).map((s) => ({
      id: `session-${s.id}`,
      type: "session",
      title: s.title || "Untitled session",
      subtitle: `${s.messages?.length || 0} messages`,
      meta: formatDate(s.updatedAt),
    })),
    ...notes.slice(0, 2).map((n) => ({
      id: `note-${n.id}`,
      type: "note",
      title: n.title,
      subtitle: "Note saved",
      meta: formatDate(n.createdAt),
    })),
  ]
    .sort(() => 0) // preserve insertion order (newest first from API)
    .slice(0, 7);

  return (
    <div className="rounded-3xl border border-border/60 bg-card p-6" style={{ boxShadow: "0 2px 12px rgba(0,0,0,0.04)" }}>
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div>
          <h3 className="font-bold text-base text-foreground flex items-center gap-2">
            <Zap size={16} className="text-primary" />
            Recent Activity
          </h3>
          <p className="text-xs text-muted-foreground mt-0.5">Latest events across your workspace</p>
        </div>
        <span className="flex h-2 w-2 rounded-full bg-emerald-500 animate-pulse" title="Live" />
      </div>

      {activity.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-40 rounded-2xl border border-dashed border-border text-center text-sm text-muted-foreground gap-2">
          <Clock size={24} className="opacity-30" />
          <p>No activity yet. Create an agent or start a chat.</p>
        </div>
      ) : (
        <div className="relative">
          {/* Vertical timeline line */}
          <div className="absolute left-5 top-4 bottom-4 w-px bg-border/60" />

          <div className="space-y-1">
            <AnimatePresence>
              {activity.map((item, i) => {
                const cfg = iconMap[item.type];
                const ItemIcon = cfg.icon;
                return (
                  <motion.div
                    key={item.id}
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.06, duration: 0.3 }}
                    className="flex items-center gap-3 pl-1 pr-3 py-2.5 rounded-2xl hover:bg-muted/40 transition-colors group cursor-default"
                  >
                    {/* Icon with timeline dot */}
                    <div
                      className="relative flex h-9 w-9 shrink-0 items-center justify-center rounded-xl z-10 group-hover:scale-105 transition-transform"
                      style={{ background: cfg.bg }}
                    >
                      <ItemIcon size={15} style={{ color: cfg.color }} />
                    </div>

                    {/* Text */}
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold text-foreground truncate">{item.title}</span>
                        <span
                          className="text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-full shrink-0"
                          style={{ background: cfg.bg, color: cfg.color }}
                        >
                          {cfg.label}
                        </span>
                      </div>
                      <div className="text-xs text-muted-foreground mt-0.5 flex items-center gap-1.5">
                        <span>{item.subtitle}</span>
                        <span className="opacity-40">·</span>
                        <span>{item.meta}</span>
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </AnimatePresence>
          </div>
        </div>
      )}
    </div>
  );
}

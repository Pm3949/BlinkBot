import { motion } from "framer-motion";
import { Bot, ChevronRight, Cpu, Network, ExternalLink } from "lucide-react";
import { Link } from "react-router-dom";

const providerColors = {
  groq: "#f97316",
  openai: "#10b981",
  gemini: "#6366f1",
  anthropic: "#8b5cf6",
  ollama: "#06b6d4",
};

export default function RecentAgents({ agents = [], isLoading = false }) {
  const recentAgents = agents.slice(0, 5);

  return (
    <div
      className="rounded-3xl border border-border/60 bg-card p-6 flex flex-col"
      style={{ boxShadow: "0 2px 12px rgba(0,0,0,0.04)" }}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div>
          <h3 className="font-bold text-base text-foreground">Active Agents</h3>
          <p className="text-xs text-muted-foreground mt-0.5">Quick access to studio</p>
        </div>
        <Link
          to="/studio"
          className="flex items-center gap-1 text-xs font-semibold text-primary hover:underline underline-offset-2 transition-all"
        >
          View All
          <ExternalLink size={11} />
        </Link>
      </div>

      {/* Loading skeletons */}
      {isLoading && (
        <div className="space-y-2.5">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-14 rounded-2xl bg-muted/40 animate-pulse" />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!isLoading && recentAgents.length === 0 && (
        <div className="flex flex-col items-center justify-center flex-1 h-44 rounded-2xl border border-dashed border-border text-center text-sm text-muted-foreground gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/8" style={{ background: "rgba(255,77,0,0.08)" }}>
            <Bot size={22} style={{ color: "var(--primary)" }} />
          </div>
          <div>
            <p className="font-medium text-foreground text-sm">No agents yet</p>
            <p className="text-xs mt-0.5">Create your first agent in Studio</p>
          </div>
        </div>
      )}

      {/* Agent list */}
      {!isLoading && (
        <div className="space-y-2">
          {recentAgents.map((agent, i) => {
            const providerColor = providerColors[agent.llm_provider?.toLowerCase()] || "var(--primary)";
            const isNetworkAgent = !!agent.project_id;
            return (
              <motion.div
                key={agent.id}
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.06 }}
              >
                <Link
                  to={isNetworkAgent ? `/studio/project/${agent.project_id}` : "/studio"}
                  className="flex items-center gap-3 p-3 rounded-2xl border border-border/40 hover:border-primary/20 hover:bg-muted/30 transition-all group"
                >
                  {/* Avatar */}
                  <div
                    className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl group-hover:scale-105 transition-transform"
                    style={{ background: `${providerColor}18` }}
                  >
                    {isNetworkAgent ? (
                      <Network size={16} style={{ color: providerColor }} />
                    ) : (
                      <Bot size={16} style={{ color: providerColor }} />
                    )}
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span className="text-sm font-semibold text-foreground truncate">{agent.name}</span>
                      {agent.is_active && (
                        <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse shrink-0" />
                      )}
                    </div>
                    <div className="flex items-center gap-1 mt-0.5 text-[11px] text-muted-foreground">
                      <Cpu size={9} />
                      <span className="truncate">{agent.llm_model || "Default"}</span>
                      {isNetworkAgent && (
                        <>
                          <span className="opacity-40">·</span>
                          <span className="text-[10px] font-semibold" style={{ color: providerColor }}>Network</span>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Arrow */}
                  <div
                    className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-border/50 group-hover:border-primary/30 group-hover:text-primary transition-all text-muted-foreground"
                  >
                    <ChevronRight size={13} />
                  </div>
                </Link>
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
}

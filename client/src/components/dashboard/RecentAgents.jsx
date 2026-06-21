import { Bot, ChevronRight, Cpu } from "lucide-react";
import { Link } from "react-router-dom";

export default function RecentAgents({
  agents = [],
  isLoading = false,
}) {
  const recentAgents = agents.slice(0, 4); // Show up to 4 agents

  return (
    <div
      className="
        glass-card
        p-6
        flex
        flex-col
        h-full
      "
    >
      <div className="flex justify-between items-center mb-6">
        <div>
          <h3 className="font-bold text-lg text-foreground">
            Active Agents
          </h3>
          <p className="text-xs text-muted-foreground mt-0.5">Quick access to playground</p>
        </div>

        <Link
          to="/playground"
          className="text-xs font-semibold bg-primary/10 text-primary hover:bg-primary/20 px-3 py-1.5 rounded-full transition-all flex items-center gap-1 group"
        >
          View All
          <ChevronRight size={12} className="group-hover:translate-x-0.5 transition-transform" />
        </Link>
      </div>

      <div className="space-y-3 flex-1">
        {isLoading && (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-16 rounded-2xl bg-muted/40 animate-pulse border border-border/50" />
            ))}
          </div>
        )}

        {!isLoading && recentAgents.length === 0 && (
          <div className="flex flex-col items-center justify-center h-48 rounded-2xl border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
            <Bot size={28} className="text-muted-foreground/30 mb-2" />
            <p>No agents created yet.</p>
          </div>
        )}

        {!isLoading && recentAgents.map((agent) => (
          <Link
            key={agent.id}
            to={agent.project_id ? `/playground/project/${agent.project_id}` : "/playground"}
            className="
              flex
              items-center
              justify-between
              p-3.5
              rounded-2xl
              bg-muted/10
              hover:bg-muted/30
              border
              border-border/30
              hover:border-primary/20
              transition-all
              group
            "
          >
            <div className="flex items-center gap-3.5 min-w-0">
              <div
                className="
                  h-10
                  w-10
                  rounded-xl
                  bg-primary/10
                  text-primary
                  flex
                  items-center
                  justify-center
                  shrink-0
                  group-hover:scale-105
                  transition-transform
                "
              >
                <Bot size={18} />
              </div>

              <div className="min-w-0">
                <div className="font-semibold text-sm text-foreground truncate flex items-center gap-2">
                  {agent.name}
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse shrink-0" title="Ready" />
                </div>

                <div className="text-xs text-muted-foreground flex items-center gap-1 mt-0.5">
                  <Cpu size={10} />
                  <span className="truncate">{agent.model || "Default Model"}</span>
                </div>
              </div>
            </div>

            <div className="h-7 w-7 rounded-lg bg-background border border-border group-hover:bg-primary/10 group-hover:text-primary group-hover:border-primary/20 flex items-center justify-center text-muted-foreground transition-all shrink-0">
              <ChevronRight size={14} />
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}


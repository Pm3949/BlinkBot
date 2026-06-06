import { Bot } from "lucide-react";
import { Link } from "react-router-dom";

export default function RecentAgents({
  agents = [],
  isLoading = false,
}) {
  const recentAgents = agents.slice(0, 3);

  return (
    <div
      className="
      glass-card
      p-6
    "
    >
      <div className="flex justify-between mb-6">
        <h3 className="font-semibold text-lg text-foreground">
          Recent Agents
        </h3>

        <Link
          to="/agents"
          className="text-primary hover:text-primary-hover transition-colors text-sm"
        >
          View All
        </Link>
      </div>

      <div className="space-y-4">
        {isLoading && (
          <div className="space-y-3">
            <div className="h-20 rounded-2xl bg-slate-100 animate-pulse" />
            <div className="h-20 rounded-2xl bg-slate-100 animate-pulse" />
            <div className="h-20 rounded-2xl bg-slate-100 animate-pulse" />
          </div>
        )}

        {!isLoading && recentAgents.length === 0 && (
          <div className="rounded-2xl border border-dashed border-border p-6 text-sm text-muted-foreground">
            No agents created yet.
          </div>
        )}

        {!isLoading && recentAgents.map((agent) => (
          <Link
            key={agent.id}
            to="/agents"
            className="
            flex
            items-center
            gap-4
            p-4
            rounded-2xl
            hover:bg-muted
            transition-colors
          "
          >
            <div
              className="
              h-12
              w-12
              rounded-2xl
              bg-primary/10
              flex
              items-center
              justify-center
            "
            >
              <Bot className="text-[var(--primary)]" />
            </div>

            <div>
              <div className="font-medium text-foreground">
                {agent.name}
              </div>

              <div className="text-sm text-muted-foreground">
                {agent.model}
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

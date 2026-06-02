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
      bg-white
      dark:bg-zinc-900
      rounded-2xl
      border
      border-slate-200
      dark:border-zinc-800
      p-6
    "
    >
      <div className="flex justify-between mb-6">
        <h3 className="font-semibold text-lg">
          Recent Agents
        </h3>

        <Link
          to="/agents"
          className="text-indigo-600 dark:text-indigo-300"
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
          <div className="rounded-2xl border border-dashed border-slate-200 p-6 text-sm text-slate-500 dark:border-zinc-800 dark:text-zinc-400">
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
            hover:bg-slate-50
            dark:hover:bg-zinc-800
          "
          >
            <div
              className="
              h-12
              w-12
              rounded-2xl
              bg-indigo-100
              dark:bg-indigo-500/15
              flex
              items-center
              justify-center
            "
            >
              <Bot className="text-indigo-600" />
            </div>

            <div>
              <div className="font-medium">
                {agent.name}
              </div>

              <div className="text-sm text-slate-500 dark:text-zinc-400">
                {agent.model}
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

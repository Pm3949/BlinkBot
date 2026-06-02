import { Bot, BookOpen, MessageSquare } from "lucide-react";

function formatDate(value) {
  if (!value) return "Recently";

  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

export default function ActivityFeed({
  agents = [],
  sessions = [],
  notes = [],
}) {
  const activity = [
    ...agents.slice(0, 3).map((agent) => ({
      id: `agent-${agent.id}`,
      icon: Bot,
      title: `${agent.name} created`,
      meta: formatDate(agent.created_at),
    })),
    ...sessions.slice(0, 3).map((session) => ({
      id: `session-${session.id}`,
      icon: MessageSquare,
      title: session.title,
      meta: `${session.messages.length} messages · ${formatDate(session.updatedAt)}`,
    })),
    ...notes.slice(0, 3).map((note) => ({
      id: `note-${note.id}`,
      icon: BookOpen,
      title: note.title,
      meta: formatDate(note.createdAt),
    })),
  ].slice(0, 6);

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <h3 className="mb-6 text-lg font-semibold text-slate-950 dark:text-zinc-50">
        Recent Activity
      </h3>

      {activity.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-200 p-6 text-sm text-slate-500 dark:border-zinc-800 dark:text-zinc-400">
          Create an agent, start a chat, or save a note to see activity here.
        </div>
      ) : (
        <div className="space-y-3">
          {activity.map((item) => (
            <div
              key={item.id}
              className="flex items-center gap-3 rounded-2xl border border-slate-100 p-3 transition hover:bg-slate-50 dark:border-zinc-800 dark:hover:bg-zinc-800/70"
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 dark:bg-indigo-500/15 dark:text-indigo-300">
                <item.icon size={17} />
              </div>

              <div className="min-w-0">
                <div className="truncate text-sm font-medium text-slate-800 dark:text-zinc-100">
                  {item.title}
                </div>

                <div className="text-xs text-slate-500 dark:text-zinc-400">
                  {item.meta}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

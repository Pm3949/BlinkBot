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
    <div className="glass-card p-6">
      <h3 className="mb-6 text-lg font-semibold text-foreground">
        Recent Activity
      </h3>

      {activity.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-border p-6 text-sm text-muted-foreground">
          Create an agent, start a chat, or save a note to see activity here.
        </div>
      ) : (
        <div className="space-y-3">
          {activity.map((item) => (
            <div
              key={item.id}
              className="flex items-center gap-3 rounded-2xl border border-border p-3 transition hover:bg-muted"
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
                <item.icon size={17} />
              </div>

              <div className="min-w-0">
                <div className="truncate text-sm font-medium text-foreground">
                  {item.title}
                </div>

                <div className="text-xs text-muted-foreground">
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

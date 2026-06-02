import { useState } from "react";
import {
  Plus,
  Bot,
  MessageSquare,
  MoreVertical,
  Pencil,
  Trash2,
  Bookmark,
  Pin,
} from "lucide-react";

export default function ChatSidebar({
  agents = [],
  activeAgentId,
  activeSessionId,
  sessions = [],
  onAgentSelect,
  onNewChat,
  onSessionSelect,
  onRenameSession,
  onTogglePinSession,
  onDeleteSession,
  onSaveSession,
}) {
  const [openMenuId, setOpenMenuId] = useState(null);
  const sortedSessions = [...sessions].sort(
    (first, second) =>
      Number(Boolean(second.pinned)) - Number(Boolean(first.pinned)) ||
      new Date(second.updatedAt).getTime() - new Date(first.updatedAt).getTime(),
  );

  const handleRename = (session) => {
    const title = window.prompt("Rename chat", session.title);

    if (title !== null) {
      onRenameSession(session.id, title);
    }

    setOpenMenuId(null);
  };

  const handleDelete = (sessionId) => {
    onDeleteSession(sessionId);
    setOpenMenuId(null);
  };

  const handleSave = (session) => {
    onSaveSession(session);
    setOpenMenuId(null);
  };

  return (
    <div className="w-80 border-r border-slate-200 bg-white flex flex-col dark:border-zinc-800 dark:bg-zinc-950">
      <div className="p-5">
        <button
          type="button"
          onClick={onNewChat}
          disabled={!activeAgentId}
          className="
          w-full
          flex
          items-center
          justify-center
          gap-2
          py-3
          rounded-2xl
          bg-indigo-600
          text-white
          hover:bg-indigo-700
          disabled:opacity-60
        "
        >
          <Plus size={18} />
          New Chat
        </button>
      </div>

      <div className="border-t border-slate-100 px-3 py-4 dark:border-zinc-800">
        <div className="text-xs uppercase text-slate-400 px-3 mb-3 dark:text-zinc-500">
          Agents
        </div>

        {agents.length === 0 && (
          <div className="px-3 py-4 text-sm text-slate-500 dark:text-zinc-400">
            No agents available.
          </div>
        )}

        {agents.map((agent) => (
          <button
            key={agent.id}
            type="button"
            onClick={() => onAgentSelect(agent.id)}
            className={`
            w-full
            flex
            items-center
            justify-between
            p-3
            rounded-2xl
            mb-1
            ${
              activeAgentId === agent.id
                ? "bg-indigo-50 text-indigo-700 dark:bg-indigo-500/15 dark:text-indigo-300"
                : "hover:bg-slate-100 dark:text-zinc-300 dark:hover:bg-zinc-900"
            }
          `}
          >
            <div className="flex items-center gap-3 min-w-0">
              <Bot size={16} />
              <span className="text-sm truncate">
                {agent.name}
              </span>
            </div>
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto border-t border-slate-100 px-3 py-4 dark:border-zinc-800">
        <div className="mb-3 px-3 text-xs uppercase text-slate-400 dark:text-zinc-500">
          Chat History
        </div>

        {!activeAgentId && (
          <div className="px-3 py-3 text-sm text-slate-500 dark:text-zinc-400">
            Select an agent to view chat history.
          </div>
        )}

        {activeAgentId && sessions.length === 0 && (
          <div className="px-3 py-3 text-sm text-slate-500 dark:text-zinc-400">
            No chat history for this agent.
          </div>
        )}

        <div className="space-y-1">
          {sortedSessions.map((session) => (
            <div key={session.id} className="relative">
              <button
                type="button"
                onClick={() => onSessionSelect(session)}
                className={`
                w-full
                rounded-2xl
                p-3
                pr-11
                text-left
                ${
                  activeSessionId === session.id
                    ? "bg-slate-900 text-white dark:bg-indigo-500/20 dark:text-indigo-200"
                    : "hover:bg-slate-100 dark:text-zinc-200 dark:hover:bg-zinc-900"
                }
              `}
              >
                <div className="flex items-center gap-3 min-w-0">
                  <MessageSquare size={16} className="shrink-0" />
                  <div className="min-w-0">
                    <div className="truncate text-sm font-medium">
                      {session.title}
                    </div>
                    <div
                      className={`truncate text-xs ${
                        activeSessionId === session.id
                          ? "text-slate-300"
                          : "text-slate-500"
                      }`}
                    >
                      {new Date(session.updatedAt).toLocaleDateString()}
                    </div>
                  </div>
                  {session.pinned && (
                    <Pin
                      size={13}
                      fill="currentColor"
                      className="ml-auto shrink-0"
                    />
                  )}
                </div>
              </button>

              <button
                type="button"
                onClick={(event) => {
                  event.stopPropagation();
                  setOpenMenuId(openMenuId === session.id ? null : session.id);
                }}
                className={`
                absolute
                right-2
                top-2
                rounded-xl
                p-2
                ${
                  activeSessionId === session.id
                    ? "text-white hover:bg-white/10"
                    : "text-slate-500 hover:bg-slate-200"
                }
              `}
                title="Chat actions"
              >
                <MoreVertical size={16} />
              </button>

              {openMenuId === session.id && (
                <div className="absolute right-2 top-11 z-20 w-44 rounded-2xl border border-slate-200 bg-white p-1 shadow-lg dark:border-zinc-800 dark:bg-zinc-900">
                  <button
                    type="button"
                    onClick={() => {
                      onTogglePinSession(session.id);
                      setOpenMenuId(null);
                    }}
                    className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-100 dark:text-zinc-200 dark:hover:bg-zinc-800"
                  >
                    <Pin
                      size={15}
                      fill={session.pinned ? "currentColor" : "none"}
                    />
                    {session.pinned ? "Unpin" : "Pin"}
                  </button>

                  <button
                    type="button"
                    onClick={() => handleRename(session)}
                    className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-100 dark:text-zinc-200 dark:hover:bg-zinc-800"
                  >
                    <Pencil size={15} />
                    Rename
                  </button>

                  <button
                    type="button"
                    onClick={() => handleSave(session)}
                    disabled={session.messages.length === 0}
                    className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-100 disabled:opacity-50 dark:text-zinc-200 dark:hover:bg-zinc-800"
                  >
                    <Bookmark size={15} />
                    Save to notes
                  </button>

                  <button
                    type="button"
                    onClick={() => handleDelete(session.id)}
                    className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm text-red-600 hover:bg-red-50 dark:text-red-300 dark:hover:bg-red-500/10"
                  >
                    <Trash2 size={15} />
                    Delete
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

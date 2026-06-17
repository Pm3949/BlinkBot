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

import { useProjectSubAgents } from "../../hooks/useAgents";
import { ChevronRight, ChevronDown, Network } from "lucide-react";

export default function ChatSidebar({
  standaloneAgents = [],
  projects = [],
  activeAgentId,
  activeSessionId,
  sessions = [],
  onAgentSelect,
  onNewChat,
  onSessionSelect,
  onRenameSession,
  onTogglePinSession,
  onDeleteSession,
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

  const ProjectFolder = ({ project }) => {
    const [isExpanded, setIsExpanded] = useState(false);
    const { data: subAgents = [], isLoading } = useProjectSubAgents(isExpanded ? project.id : null);

    return (
      <div className="mb-2">
        <button
          type="button"
          onClick={() => setIsExpanded(!isExpanded)}
          className="w-full flex items-center justify-between p-2 rounded-xl text-muted-foreground hover:bg-muted transition"
        >
          <div className="flex items-center gap-2">
            <Network size={16} />
            <span className="text-sm font-medium truncate">{project.name}</span>
          </div>
          {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </button>

        {isExpanded && (
          <div className="ml-4 pl-2 mt-1 border-l border-border space-y-1">
            {isLoading ? (
              <div className="text-xs text-muted-foreground py-2 pl-2">Loading...</div>
            ) : subAgents.length === 0 ? (
              <div className="text-xs text-muted-foreground py-2 pl-2">No agents found</div>
            ) : (
              subAgents.map(agent => (
                <button
                  key={agent.id}
                  type="button"
                  onClick={() => onAgentSelect(agent)}
                  className={`w-full flex items-center gap-2 p-2 rounded-xl text-sm transition ${
                    activeAgentId === agent.id
                      ? "bg-primary/10 text-primary"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground"
                  }`}
                >
                  <Bot size={14} />
                  <span className="truncate">{agent.name}</span>
                </button>
              ))
            )}
          </div>
        )}
      </div>
    );
  };
  return (
    <div className="w-80 border-r border-border bg-card flex flex-col">
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
          btn-primary
          disabled:opacity-60
        "
        >
          <Plus size={18} />
          New Chat
        </button>
      </div>

      <div className="border-t border-border px-3 py-4">
        <div className="text-xs uppercase text-muted-foreground px-3 mb-3">
          Agents
        </div>

        {standaloneAgents.length === 0 && projects.length === 0 && (
          <div className="px-3 py-4 text-sm text-muted-foreground">
            No agents or networks available.
          </div>
        )}

        {standaloneAgents.map((agent) => (
          <button
            key={agent.id}
            type="button"
            onClick={() => onAgentSelect(agent)}
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
                ? "bg-primary/10 text-primary"
                : "text-muted-foreground hover:bg-muted hover:text-foreground"
            }
          `}
          >
            <div className="flex items-center gap-3 min-w-0">
              <Bot size={16} />
              <span className="text-sm font-medium truncate">
                {agent.name}
              </span>
            </div>
          </button>
        ))}

        {projects.length > 0 && (
          <div className="mt-4 pt-4 border-t border-border">
            <div className="text-xs uppercase text-muted-foreground px-3 mb-3">
              Networks
            </div>
            {projects.map((project) => (
              <ProjectFolder key={project.id} project={project} />
            ))}
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto border-t border-border px-3 py-4">
        <div className="mb-3 px-3 text-xs uppercase text-muted-foreground">
          Chat History
        </div>

        {!activeAgentId && (
          <div className="px-3 py-3 text-sm text-muted-foreground">
            Select an agent to view chat history.
          </div>
        )}

        {activeAgentId && sessions.length === 0 && (
          <div className="px-3 py-3 text-sm text-muted-foreground">
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
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
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
                          ? "text-primary-foreground/70"
                          : "text-muted-foreground"
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
                    ? "text-primary-foreground hover:bg-primary-foreground/10"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                }
              `}
                title="Chat actions"
              >
                <MoreVertical size={16} />
              </button>

              {openMenuId === session.id && (
                <div className="absolute right-2 top-11 z-20 w-44 rounded-2xl border border-border bg-card p-1 shadow-lg">
                  <button
                    type="button"
                    onClick={() => {
                      onTogglePinSession(session.id);
                      setOpenMenuId(null);
                    }}
                    className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm text-foreground hover:bg-muted"
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
                    className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm text-foreground hover:bg-muted"
                  >
                    <Pencil size={15} />
                    Rename
                  </button>



                  <button
                    type="button"
                    onClick={() => handleDelete(session.id)}
                    className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm text-red-600 hover:bg-red-500/10"
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

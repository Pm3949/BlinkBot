import { useMemo, useState } from "react";
import { toast } from "sonner";
import ChatSidebar from "../components/chat/ChatSidebar";
import ChatComposer from "../components/chat/ChatComposer";
import MessageBubble from "../components/chat/MessageBubble";
import ContextPanel from "../components/chat/ContextPanel";
import { useAuth } from "../context/AuthContext";
import { useAgents } from "../hooks/useAgents";
import { useChat } from "../hooks/useChat";
import { useDocuments } from "../hooks/useDocuments";
import { useNotes } from "../hooks/useNotes";
import LoadingSkeleton from "../components/shared/LoadingSkeleton";

export default function ChatPage() {
  const { user } = useAuth();
  const { data: agents = [], isLoading: isLoadingAgents } = useAgents(user?.id);
  const [activeAgentId, setActiveAgentId] = useState("");
  const {
    activeSessionId,
    activeSession,
    sessions,
    messages,
    loading,
    sendMessage,
    startNewChat,
    selectSession,
    renameSession,
    togglePinSession,
    deleteSession,
  } = useChat();
  const { addNote } = useNotes();

  const selectedAgentId =
    activeAgentId || activeSession?.agentId || agents[0]?.id || "";

  const activeAgent = useMemo(
    () => agents.find((agent) => agent.id === selectedAgentId),
    [selectedAgentId, agents],
  );

  const { data: documents = [], isLoading: isLoadingDocuments } =
    useDocuments(selectedAgentId);

  const selectedAgentSessions = useMemo(
    () =>
      sessions.filter(
        (session) =>
          String(session.agentId || "general") === String(selectedAgentId),
      ),
    [sessions, selectedAgentId],
  );

  const isActiveSessionForSelectedAgent =
    String(activeSession?.agentId || "general") === String(selectedAgentId);
  const visibleMessages = isActiveSessionForSelectedAgent ? messages : [];

  const handleAgentSelect = (agentId) => {
    setActiveAgentId(agentId);
    const latestAgentSession = sessions
      .filter(
        (session) => String(session.agentId || "general") === String(agentId),
      )
      .sort(
        (first, second) =>
          Number(Boolean(second.pinned)) - Number(Boolean(first.pinned)) ||
          new Date(second.updatedAt).getTime() -
            new Date(first.updatedAt).getTime(),
      )[0];

    selectSession(latestAgentSession?.id || null);
  };

  const handleNewChat = () => {
    startNewChat({
      agentId: selectedAgentId || null,
      agentName: activeAgent?.name || "General",
    });
  };

  const handleSessionSelect = (session) => {
    selectSession(session.id);

    if (session.agentId) {
      setActiveAgentId(session.agentId);
    }
  };

  const handleSend = (content) => {
    sendMessage({
      agentId: selectedAgentId,
      agentName: activeAgent?.name || "General",
      content,
    });
  };

  const handleSaveSession = (session) => {
    const chatContent = session.messages
      .filter((message) => message.content?.trim())
      .map(
        (message) =>
          `**${message.role === "user" ? "You" : "Assistant"}:**\n\n${
            message.content
          }`,
      )
      .join("\n\n---\n\n");

    if (!chatContent) {
      toast.error("This chat has no messages to save.");
      return;
    }

    const note = addNote(
      `# Chat: ${session.title}\n\nAgent: ${
        session.agentName || "General"
      }\n\n${chatContent}`,
      {
        id: session.agentId,
        name: session.agentName || "General",
      },
    );

    if (note) {
      toast.success("Full chat saved to notes");
    }
  };

  return (
    <div className="flex h-[calc(100vh-8rem)] overflow-hidden rounded-2xl border border-slate-200 bg-slate-50 shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
      <ChatSidebar
        agents={agents}
        activeAgentId={selectedAgentId}
        activeSessionId={isActiveSessionForSelectedAgent ? activeSessionId : null}
        sessions={selectedAgentSessions}
        onAgentSelect={handleAgentSelect}
        onNewChat={handleNewChat}
        onSessionSelect={handleSessionSelect}
        onRenameSession={renameSession}
        onTogglePinSession={togglePinSession}
        onDeleteSession={deleteSession}
        onSaveSession={handleSaveSession}
      />

      <div className="flex-1 flex flex-col">
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-4xl mx-auto px-8 py-10 space-y-8">
            {isLoadingAgents && <LoadingSkeleton count={2} className="h-24" />}

            {!isLoadingAgents && agents.length === 0 && (
              <div className="text-sm text-slate-500 dark:text-zinc-400">
                Create an agent before starting a chat.
              </div>
            )}

            {!isLoadingAgents &&
              agents.length > 0 &&
              visibleMessages.length === 0 && (
              <div className="rounded-2xl border border-dashed border-slate-200 bg-white p-8 text-center dark:border-zinc-800 dark:bg-zinc-900">
                <h3 className="font-semibold text-slate-900 dark:text-zinc-50">
                  {activeAgent ? activeAgent.name : "Start a chat"}
                </h3>

                <p className="mt-2 text-sm text-slate-500 dark:text-zinc-400">
                  Select a chat from history or start a new chat with this agent.
                </p>
              </div>
            )}

            {visibleMessages.map((message) => (
              <MessageBubble
                key={message.id}
                role={message.role}
                agent={activeAgent}
                content={
                  message.content ||
                  (message.role === "assistant" ? "Thinking..." : "")
                }
              />
            ))}

            {loading && (
              <div className="flex gap-2 px-4 py-2">
                <div className="h-2 w-2 rounded-full bg-slate-400 animate-bounce" />
                <div className="h-2 w-2 rounded-full bg-slate-400 animate-bounce [animation-delay:150ms]" />
                <div className="h-2 w-2 rounded-full bg-slate-400 animate-bounce [animation-delay:300ms]" />
              </div>
            )}
          </div>
        </div>

        <ChatComposer
          disabled={!selectedAgentId}
          isLoading={loading}
          onSend={handleSend}
        />
      </div>

      <ContextPanel documents={documents} isLoading={isLoadingDocuments} />
    </div>
  );
}

import { toast } from "sonner";
import { streamChat } from "../services/chatService";
import { useChatStore } from "../store/useChatStore";

export function useChat() {
  const {
    activeSessionId,
    sessions,
    addMessage,
    updateLastAssistantMessage,
    startSession,
    selectSession,
    renameSession,
    togglePinSession,
    deleteSession,
    ensureSession,
    isTyping,
    setTyping,
  } = useChatStore();
  const activeSession = sessions.find((session) => session.id === activeSessionId);
  const messages = activeSession?.messages || [];

  const sendMessage = async ({ agentId, agentName, content }) => {
    const message = content.trim();

    if (!agentId) {
      toast.error("Select an agent before starting chat.");
      return;
    }

    if (!message) return;

    const session = ensureSession({
      agentId,
      agentName,
    });

    const userMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: message,
    };

    const assistantMessage = {
      id: crypto.randomUUID(),
      role: "assistant",
      content: "",
    };

    const history = session.messages.map(({ role, content: itemContent }) => ({
      role,
      content: itemContent,
    }));

    addMessage(userMessage, {
      agentId,
      agentName,
    });
    addMessage(assistantMessage, {
      agentId,
      agentName,
    });

    setTyping(true);

    try {
      await streamChat(
        {
          agent_id: agentId,
          message,
          history,
        },
        (streamedText) => {
          updateLastAssistantMessage(streamedText);
        },
      );
    } catch (error) {
      toast.error(error.message || "Unable to get a response.");
    } finally {
      setTyping(false);
    }
  };

  const startNewChat = ({ agentId, agentName } = {}) =>
    startSession({
      agentId,
      agentName,
    });

  return {
    activeSessionId,
    activeSession,
    sessions,
    messages,
    loading: isTyping,
    sendMessage,
    startNewChat,
    selectSession,
    renameSession,
    togglePinSession,
    deleteSession,
  };
}

import { create } from "zustand";

const SESSIONS_KEY = "ragmate_chat_sessions";
const ACTIVE_SESSION_KEY = "ragmate_active_chat_session";
const LEGACY_MESSAGES_KEY = "chat_messages";

function readJson(key, fallback) {
  try {
    return JSON.parse(localStorage.getItem(key) || JSON.stringify(fallback));
  } catch {
    return fallback;
  }
}

function normalizeAgentId(agentId) {
  return agentId == null ? null : String(agentId);
}

function createSession({ agentId = null, agentName = "General", title } = {}) {
  const now = new Date().toISOString();

  return {
    id: crypto.randomUUID(),
    title: title || "New chat",
    agentId: normalizeAgentId(agentId),
    agentName,
    messages: [],
    pinned: false,
    createdAt: now,
    updatedAt: now,
  };
}

function getInitialSessions() {
  const sessions = readJson(SESSIONS_KEY, []);

  if (sessions.length > 0) return sessions;

  const legacyMessages = readJson(LEGACY_MESSAGES_KEY, []);

  if (legacyMessages.length === 0) return [];

  const migratedSession = createSession({
    title: "Previous chat",
  });

  return [
    {
      ...migratedSession,
      messages: legacyMessages,
    },
  ];
}

function persist(sessions, activeSessionId) {
  localStorage.setItem(SESSIONS_KEY, JSON.stringify(sessions));

  if (activeSessionId) {
    localStorage.setItem(ACTIVE_SESSION_KEY, activeSessionId);
  } else {
    localStorage.removeItem(ACTIVE_SESSION_KEY);
  }
}

const initialSessions = getInitialSessions();
const storedActiveSessionId = localStorage.getItem(ACTIVE_SESSION_KEY);
const initialActiveSessionId =
  initialSessions.find((session) => session.id === storedActiveSessionId)?.id ||
  initialSessions[0]?.id ||
  null;

persist(initialSessions, initialActiveSessionId);

export const useChatStore = create((set, get) => ({
  activeSessionId: initialActiveSessionId,
  sessions: initialSessions,
  isTyping: false,

  get activeSession() {
    return get().sessions.find(
      (session) => session.id === get().activeSessionId,
    );
  },

  get messages() {
    return get().activeSession?.messages || [];
  },

  startSession: ({ agentId, agentName } = {}) => {
    const session = createSession({
      agentId: normalizeAgentId(agentId),
      agentName,
    });
    const sessions = [session, ...get().sessions];

    persist(sessions, session.id);
    set({
      sessions,
      activeSessionId: session.id,
    });

    return session;
  },

  selectSession: (sessionId) => {
    persist(get().sessions, sessionId);
    set({
      activeSessionId: sessionId,
    });
  },

  ensureSession: ({ agentId, agentName } = {}) => {
    const activeSession = get().activeSession;

    if (activeSession) {
      // If we already have an active session, continue it instead of creating a new one.
      return activeSession;
    }

    return get().startSession({
      agentId,
      agentName,
    });
  },

  renameSession: (sessionId, title) => {
    const nextTitle = title.trim();

    if (!nextTitle) return;

    const sessions = get().sessions.map((session) =>
      session.id === sessionId
        ? {
            ...session,
            title: nextTitle,
            updatedAt: new Date().toISOString(),
          }
        : session,
    );

    persist(sessions, get().activeSessionId);
    set({ sessions });
  },

  togglePinSession: (sessionId) => {
    const sessions = get().sessions.map((session) =>
      session.id === sessionId
        ? {
            ...session,
            pinned: !session.pinned,
            updatedAt: new Date().toISOString(),
          }
        : session,
    );

    persist(sessions, get().activeSessionId);
    set({ sessions });
  },

  deleteSession: (sessionId) => {
    const sessions = get().sessions.filter((session) => session.id !== sessionId);
    const activeSessionId =
      get().activeSessionId === sessionId ? null : get().activeSessionId;

    persist(sessions, activeSessionId);
    set({
      sessions,
      activeSessionId,
    });
  },

  addMessage: (message, sessionDetails = {}) =>
    set((state) => {
      const normalizedSessionDetails = {
        ...sessionDetails,
        agentId: normalizeAgentId(sessionDetails.agentId),
      };
      const activeSession =
        state.sessions.find((session) => session.id === state.activeSessionId) ||
        createSession(normalizedSessionDetails);
      const title =
        activeSession.messages.length === 0 && message.role === "user"
          ? message.content.slice(0, 72)
          : activeSession.title;
      const updatedSession = {
        ...activeSession,
        ...normalizedSessionDetails,
        title,
        messages: [...activeSession.messages, message],
        updatedAt: new Date().toISOString(),
      };
      const sessions = [
        updatedSession,
        ...state.sessions.filter((session) => session.id !== updatedSession.id),
      ];

      persist(sessions, updatedSession.id);

      return {
        sessions,
        activeSessionId: updatedSession.id,
      };
    }),

  updateLastAssistantMessage: (content) =>
    set((state) => {
      const sessions = state.sessions.map((session) => {
        if (session.id !== state.activeSessionId) return session;

        const messages = [...session.messages];
        const lastMessage = messages[messages.length - 1];

        if (lastMessage?.role === "assistant") {
          messages[messages.length - 1] = {
            ...lastMessage,
            content,
          };
        }

        return {
          ...session,
          messages,
          updatedAt: new Date().toISOString(),
        };
      });

      persist(sessions, state.activeSessionId);

      return { sessions };
    }),

  setTyping: (value) =>
    set({
      isTyping: value,
    }),
}));

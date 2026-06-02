// client/src/components/Chat.jsx
import { useState, useEffect, useRef } from "react";
import { supabase } from "../supabaseClient";
import {
  Send,
  ArrowLeft,
  Loader2,
  Bot,
  User,
  Plus,
  MessageSquare,
  Trash2,
  MoreVertical,
  Edit2,
  Check,
  X as XIcon,
  Copy,
  CheckCheck,
  Share2,
  BookmarkPlus,
  FileText,
  Download,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { useReactToPrint } from "react-to-print";

// ==========================================
// 1. CODE BLOCK COMPONENT
// ==========================================
const CodeBlock = ({ node, inline, className, children, ...props }) => {
  const [isCopied, setIsCopied] = useState(false);
  const match = /language-(\w+)/.exec(className || "");
  const language = match ? match[1] : "";

  const handleCopy = () => {
    navigator.clipboard.writeText(String(children).replace(/\n$/, ""));
    setIsCopied(true);
    toast.success("Code copied to clipboard!");
    setTimeout(() => setIsCopied(false), 2000);
  };

  if (!inline && match) {
    return (
      <div className="rounded-xl overflow-hidden my-4 border border-gray-700 bg-[#1E1E1E] shadow-md print:break-inside-avoid">
        <div className="flex items-center justify-between px-4 py-2 bg-[#2D2D2D] text-gray-300 text-xs font-sans">
          <span className="uppercase font-semibold tracking-wider text-gray-400">
            {language}
          </span>
          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 hover:text-white transition-colors focus:outline-none print:hidden"
          >
            {isCopied ? (
              <CheckCheck size={14} className="text-emerald-400" />
            ) : (
              <Copy size={14} />
            )}
            {isCopied ? "Copied!" : "Copy code"}
          </button>
        </div>
        <SyntaxHighlighter
          {...props}
          style={vscDarkPlus}
          language={language}
          PreTag="div"
          customStyle={{
            margin: 0,
            padding: "1rem",
            background: "transparent",
            fontSize: "14px",
          }}
        >
          {String(children).replace(/\n$/, "")}
        </SyntaxHighlighter>
      </div>
    );
  }
  return (
    <code
      className="bg-gray-100 text-indigo-600 px-1.5 py-0.5 rounded-md text-[13px] font-mono border border-gray-200"
      {...props}
    >
      {children}
    </code>
  );
};

// ==========================================
// 🔥 2. INDIVIDUAL NOTE COMPONENT
// ==========================================
const SingleNoteItem = ({ note, index, onRemove }) => {
  const individualPrintRef = useRef(null);

  const handlePrintIndividual = useReactToPrint({
    contentRef: individualPrintRef,
    documentTitle: `RagMate_Note_${index + 1}`,
    onAfterPrint: () => toast.success("Note Exported Successfully! 📄"),
  });

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm relative group print:shadow-none print:border-gray-300 print:mb-6 print:break-inside-avoid">
      {/* Action Buttons (Hidden in Print) */}
      <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-all z-10 bg-white shadow-sm rounded-md border border-gray-100 print:hidden">
        <button
          onClick={handlePrintIndividual}
          className="p-1.5 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-md transition-colors"
          title="Download this note as PDF"
        >
          <Download size={16} />
        </button>
        <button
          onClick={() => onRemove(note.id)}
          className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-md transition-colors"
          title="Remove from notes"
        >
          <Trash2 size={16} />
        </button>
      </div>

      {/* Content to Print */}
      <div
        ref={individualPrintRef}
        className="prose prose-sm max-w-none text-gray-800 pr-8 pt-2 print:bg-white print:p-8 print:w-full"
      >
        <div className="font-bold text-xs text-indigo-500 uppercase tracking-wider mb-3 border-b pb-2">
          RagMate Note #{index + 1}
        </div>
        <ReactMarkdown components={{ code: CodeBlock }}>
          {note.content}
        </ReactMarkdown>
      </div>
    </div>
  );
};

// ==========================================
// 3. MAIN CHAT COMPONENT
// ==========================================
export default function Chat({ agent, onBack }) {
  const queryClient = useQueryClient();
  const [input, setInput] = useState("");
  const [localMessages, setLocalMessages] = useState([]);
  const [isTyping, setIsTyping] = useState(false);
  const [activeSessionId, setActiveSessionId] = useState(null);

  const [openMenuId, setOpenMenuId] = useState(null);
  const [editingSessionId, setEditingSessionId] = useState(null);
  const [editTitleValue, setEditTitleValue] = useState("");

  const [isNotesModalOpen, setIsNotesModalOpen] = useState(false);

  const messagesEndRef = useRef(null);
  const allNotesPrintRef = useRef(null); // Reference for "Export All"

  const scrollToBottom = () =>
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  useEffect(() => {
    scrollToBottom();
  }, [localMessages, isTyping]);

  const { data: sessions = [], isLoading: loadingSessions } = useQuery({
    queryKey: ["chat_sessions", agent.id],
    queryFn: async () => {
      const { data, error } = await supabase
        .from("chat_sessions")
        .select("*")
        .eq("agent_id", agent.id)
        .order("created_at", { ascending: false });
      if (error) throw new Error(error.message);
      return data || [];
    },
  });

  const { data: dbMessages, isLoading: loadingMessages } = useQuery({
    queryKey: ["chat_messages", activeSessionId],
    queryFn: async () => {
      if (!activeSessionId) return [];
      const { data, error } = await supabase
        .from("chat_messages")
        .select("*")
        .eq("session_id", activeSessionId)
        .order("created_at", { ascending: true });
      if (error) throw new Error(error.message);
      return data || [];
    },
    enabled: !!activeSessionId,
  });

  const { data: savedNotesDB = [] } = useQuery({
    queryKey: ["saved_notes", agent.id],
    queryFn: async () => {
      const { data, error } = await supabase
        .from("chat_messages")
        .select("*, chat_sessions!inner(agent_id)")
        .eq("is_saved", true)
        .eq("chat_sessions.agent_id", agent.id)
        .order("created_at", { ascending: false });
      if (error) throw new Error(error.message);
      return data || [];
    },
  });

  useEffect(() => {
    if (activeSessionId && dbMessages && !isTyping) {
      setLocalMessages(
        dbMessages.map((m) => ({
          id: m.id,
          role: m.role,
          content: m.content,
          is_saved: m.is_saved,
        })),
      );
    } else if (!activeSessionId) {
      setLocalMessages([]);
    }
  }, [dbMessages, activeSessionId, isTyping]);

  const deleteSessionMutation = useMutation({
    mutationFn: async (sessionId) => {
      const { error } = await supabase
        .from("chat_sessions")
        .delete()
        .eq("id", sessionId);
      if (error) throw new Error(error.message);
      return sessionId;
    },
    onSuccess: (deletedId) => {
      queryClient.invalidateQueries({ queryKey: ["chat_sessions", agent.id] });
      queryClient.invalidateQueries({ queryKey: ["saved_notes", agent.id] });
      if (activeSessionId === deletedId) setActiveSessionId(null);
      toast.success("Chat deleted! 🗑️");
    },
  });

  const renameSessionMutation = useMutation({
    mutationFn: async ({ sessionId, newTitle }) => {
      const { error } = await supabase
        .from("chat_sessions")
        .update({ title: newTitle })
        .eq("id", sessionId);
      if (error) throw new Error(error.message);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["chat_sessions", agent.id] });
      setEditingSessionId(null);
      toast.success("Chat renamed! ✏️");
    },
  });

  const toggleNoteMutation = useMutation({
    mutationFn: async ({ messageId, isSaved }) => {
      const { error } = await supabase
        .from("chat_messages")
        .update({ is_saved: isSaved })
        .eq("id", messageId);
      if (error) throw new Error(error.message);
    },
    onSuccess: () => {
      // queryClient.invalidateQueries({
      //   queryKey: ["chat_messages", activeSessionId],
      // });
      queryClient.invalidateQueries({ queryKey: ["saved_notes", agent.id] });
    },
  });

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || isTyping) return;

    const userText = input.trim();
    setInput("");
    setIsTyping(true);

    let currentSessionId = activeSessionId;

    try {
      if (!currentSessionId) {
        const title =
          userText.length > 15 ? userText.substring(0, 15) + "..." : userText;
        const { data: sessionData, error: sessionError } = await supabase
          .from("chat_sessions")
          .insert([{ agent_id: agent.id, user_id: agent.user_id, title }])
          .select()
          .single();
        if (sessionError) throw new Error("DB Error: " + sessionError.message);
        currentSessionId = sessionData.id;
        setActiveSessionId(currentSessionId);
        queryClient.invalidateQueries({
          queryKey: ["chat_sessions", agent.id],
        });
      }

      await supabase
        .from("chat_messages")
        .insert([
          { session_id: currentSessionId, role: "user", content: userText },
        ]);
      const updatedHistory = [
        ...localMessages,
        { role: "user", content: userText },
      ];

      // Keep the optimistic assistant placeholder in a single state update to avoid race conditions.
      setLocalMessages([
        ...updatedHistory,
        { role: "assistant", content: "", is_saved: false },
      ]);

      const requestPayload = {
        agent_id: agent.id,
        message: userText,
        history: updatedHistory.slice(-6).map((msg) => ({
          role: String(msg.role),
          content: String(msg.content),
        })),
      };

      const res = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestPayload),
      });

      if (!res.ok) {
        const errorText = await res.text();
        throw new Error(errorText || "Backend AI Error");
      }

      if (!res.body) {
        throw new Error("Empty response body from backend");
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let fullAiResponse = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        fullAiResponse += chunk;

        setLocalMessages((prev) => {
          if (prev.length === 0) return prev;
          const newMsgs = [...prev];
          if (newMsgs[newMsgs.length - 1].role === "assistant") {
            newMsgs[newMsgs.length - 1] = {
              ...newMsgs[newMsgs.length - 1],
              content: fullAiResponse,
            };
          }
          return newMsgs;
        });
      }
      await supabase
        .from("chat_messages")
        .insert([
          {
            session_id: currentSessionId,
            role: "assistant",
            content: fullAiResponse,
          },
        ]);
    } catch (error) {
      toast.error(error.message || "Error connecting to the agent!");
      setLocalMessages((prev) => [
        ...prev.slice(0, -1),
        { role: "assistant", content: `⚠️ *Error: ${error.message}*` },
      ]);
    } finally {
      setIsTyping(false);
      if (currentSessionId)
        queryClient.invalidateQueries({
          queryKey: ["chat_messages", currentSessionId],
        });
    }
  };

  const handleRenameSubmit = (sessionId) => {
    if (editTitleValue.trim())
      renameSessionMutation.mutate({
        sessionId,
        newTitle: editTitleValue.trim(),
      });
    else setEditingSessionId(null);
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.success("Response copied to clipboard!");
  };

  const shareResponse = async (text) => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: "Response from RagMate AI",
          text: text,
        });
        toast.success("Shared successfully!");
      } catch (err) {
        console.log("Sharing cancelled");
      }
    } else {
      copyToClipboard(text);
      toast("Share not supported on this browser. Copied instead!");
    }
  };

  const handleToggleNote = (msg) => {
    if (!msg.id) {
      toast.error("Please wait for the message to save first.");
      return;
    }
    const newSavedStatus = !msg.is_saved;
    setLocalMessages((prev) =>
      prev.map((m) =>
        m.id === msg.id ? { ...m, is_saved: newSavedStatus } : m,
      ),
    );
    toggleNoteMutation.mutate({ messageId: msg.id, isSaved: newSavedStatus });
    if (newSavedStatus) toast.success("Saved to Notes! 📌");
    else toast.success("Removed from Notes");
  };

  // 🔥 EXPORT ALL NOTES FIX
  const handlePrintAllNotes = useReactToPrint({
    contentRef: allNotesPrintRef,
    documentTitle: "RagMate_Saved_Notes",
    onAfterPrint: () => toast.success("PDF Exported Successfully! 📄"),
  });

  return (
    <div className="flex h-screen bg-white" onClick={() => setOpenMenuId(null)}>
      {/* LEFT SIDEBAR */}
      <div className="w-72 bg-gray-50 border-r border-gray-200 flex flex-col hidden md:flex shrink-0">
        <div className="p-4 border-b border-gray-200 flex items-center justify-between">
          <div className="flex items-center gap-2 overflow-hidden">
            <button
              onClick={onBack}
              className="p-2 -ml-2 text-gray-500 hover:text-gray-900 hover:bg-gray-200 rounded-lg transition-colors shrink-0"
            >
              <ArrowLeft size={20} />
            </button>
            <div className="font-semibold text-gray-800 truncate">
              {agent.name}
            </div>
          </div>
          <button
            onClick={() => setIsNotesModalOpen(true)}
            className="p-2 text-indigo-600 bg-indigo-50 hover:bg-indigo-100 rounded-lg transition-colors relative"
            title="View Saved Notes"
          >
            <FileText size={18} />
            {savedNotesDB.length > 0 && (
              <span className="absolute -top-1 -right-1 bg-rose-500 text-white text-[10px] font-bold w-4 h-4 rounded-full flex items-center justify-center">
                {savedNotesDB.length}
              </span>
            )}
          </button>
        </div>

        <div className="p-4">
          <button
            onClick={() => setActiveSessionId(null)}
            className="w-full flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white py-2.5 rounded-xl font-medium shadow-sm transition-all"
          >
            <Plus size={18} /> New Chat
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-3 pb-4 space-y-1">
          {loadingSessions ? (
            <div className="flex justify-center p-4">
              <Loader2 size={16} className="animate-spin text-gray-400" />
            </div>
          ) : sessions.length === 0 ? (
            <div className="text-center text-sm text-gray-500 mt-4">
              No previous chats
            </div>
          ) : (
            sessions.map((session) => (
              <div
                key={session.id}
                onClick={() => {
                  if (editingSessionId !== session.id)
                    setActiveSessionId(session.id);
                }}
                className={`group relative flex items-center justify-between p-3 rounded-xl cursor-pointer transition-colors ${activeSessionId === session.id ? "bg-indigo-50 text-indigo-700" : "hover:bg-gray-100 text-gray-700"}`}
              >
                {editingSessionId === session.id ? (
                  <div
                    className="flex items-center gap-2 w-full"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <input
                      type="text"
                      value={editTitleValue}
                      onChange={(e) => setEditTitleValue(e.target.value)}
                      autoFocus
                      className="flex-1 min-w-0 px-2 py-1 text-sm border border-indigo-300 rounded outline-none focus:ring-2 focus:ring-indigo-500 bg-white text-gray-900"
                      onKeyDown={(e) => {
                        if (e.key === "Enter") handleRenameSubmit(session.id);
                        if (e.key === "Escape") setEditingSessionId(null);
                      }}
                    />
                    <button
                      onClick={() => handleRenameSubmit(session.id)}
                      className="text-emerald-600 hover:text-emerald-700 shrink-0"
                    >
                      <Check size={16} />
                    </button>
                    <button
                      onClick={() => setEditingSessionId(null)}
                      className="text-gray-400 hover:text-gray-600 shrink-0"
                    >
                      <XIcon size={16} />
                    </button>
                  </div>
                ) : (
                  <>
                    <div className="flex items-center gap-3 overflow-hidden">
                      <MessageSquare
                        size={16}
                        className="shrink-0 opacity-70"
                      />
                      <span
                        className="text-sm font-medium truncate"
                        title={session.title}
                      >
                        {session.title}
                      </span>
                    </div>
                    <div className="relative shrink-0 ml-2 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setOpenMenuId(
                            openMenuId === session.id ? null : session.id,
                          );
                        }}
                        className="p-1 text-gray-400 hover:text-gray-800 hover:bg-gray-200 rounded-md transition-colors"
                      >
                        <MoreVertical size={16} />
                      </button>
                      {openMenuId === session.id && (
                        <div className="absolute right-0 mt-1 w-32 bg-white rounded-xl shadow-lg border border-gray-100 py-1.5 z-20 overflow-hidden">
                          <button
                            className="w-full flex items-center gap-2 px-3 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50 text-left transition-colors"
                            onClick={(e) => {
                              e.stopPropagation();
                              setOpenMenuId(null);
                              setEditingSessionId(session.id);
                              setEditTitleValue(session.title);
                            }}
                          >
                            <Edit2 size={14} /> Rename
                          </button>
                          <button
                            className="w-full flex items-center gap-2 px-3 py-2 text-sm font-semibold text-rose-600 hover:bg-rose-50 text-left transition-colors"
                            onClick={(e) => {
                              e.stopPropagation();
                              setOpenMenuId(null);
                              if (
                                window.confirm("Delete this chat permanently?")
                              )
                                deleteSessionMutation.mutate(session.id);
                            }}
                          >
                            <Trash2 size={14} /> Delete
                          </button>
                        </div>
                      )}
                    </div>
                  </>
                )}
              </div>
            ))
          )}
        </div>
      </div>

      {/* MAIN CHAT AREA */}
      <div className="flex-1 flex flex-col h-full relative">
        <div className="md:hidden flex items-center gap-3 p-4 border-b border-gray-200 bg-white">
          <button
            onClick={onBack}
            className="p-1.5 text-gray-600 hover:bg-gray-100 rounded-lg"
          >
            <ArrowLeft size={20} />
          </button>
          <span className="font-bold text-gray-800">{agent.name}</span>

          <div className="ml-auto flex items-center gap-2">
            <button
              onClick={() => setIsNotesModalOpen(true)}
              className="p-1.5 text-indigo-600 bg-indigo-50 rounded-lg relative"
            >
              <FileText size={20} />
              {savedNotesDB.length > 0 && (
                <span className="absolute -top-1 -right-1 bg-rose-500 text-white text-[10px] font-bold w-4 h-4 rounded-full flex items-center justify-center">
                  {savedNotesDB.length}
                </span>
              )}
            </button>
            <button
              onClick={() => setActiveSessionId(null)}
              className="p-1.5 text-indigo-600 bg-indigo-50 rounded-lg"
            >
              <Plus size={20} />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 sm:p-8 scroll-smooth">
          <div className="max-w-3xl mx-auto space-y-8 pb-20">
            {loadingMessages ? (
              <div className="flex justify-center mt-20">
                <Loader2 size={32} className="animate-spin text-indigo-500" />
              </div>
            ) : localMessages.length === 0 ? (
              <div className="flex flex-col items-center justify-center mt-32 text-center">
                <div className="w-16 h-16 bg-indigo-50 text-indigo-600 rounded-full flex items-center justify-center mb-4">
                  <Bot size={32} />
                </div>
                <h3 className="text-xl font-bold text-gray-900 mb-2">
                  How can I help you today?
                </h3>
                <p className="text-gray-500 max-w-md">
                  Send a message to start a new conversation. The agent will use
                  its trained knowledge base to assist you.
                </p>
              </div>
            ) : (
              localMessages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`flex gap-4 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  {msg.role === "assistant" && (
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-blue-600 flex items-center justify-center text-white shrink-0 mt-1 shadow-md">
                      <Bot size={18} />
                    </div>
                  )}

                  <div
                    className={`flex flex-col gap-1 max-w-[85%] ${msg.role === "user" ? "items-end" : "items-start w-full"}`}
                  >
                    <div
                      className={`rounded-2xl px-5 py-3.5 shadow-sm ${msg.role === "user" ? "bg-gray-900 text-white rounded-tr-none" : "bg-white border border-gray-200 text-gray-800 rounded-tl-none w-full max-w-none"}`}
                    >
                      {msg.role === "assistant" ? (
                        msg.content ? (
                          <div className="prose prose-sm max-w-none">
                            <ReactMarkdown components={{ code: CodeBlock }}>
                              {msg.content}
                            </ReactMarkdown>
                          </div>
                        ) : (
                          <span className="flex gap-1 py-1">
                            <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></span>
                            <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-75"></span>
                            <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-150"></span>
                          </span>
                        )
                      ) : (
                        <p className="whitespace-pre-wrap text-[15px]">
                          {msg.content}
                        </p>
                      )}
                    </div>

                    {msg.role === "assistant" && msg.content && (
                      <div className="flex items-center gap-2 mt-1 px-1 text-gray-400">
                        <button
                          onClick={() => copyToClipboard(msg.content)}
                          className="p-1.5 hover:bg-gray-100 hover:text-gray-700 rounded-md transition-colors group relative"
                          title="Copy Message"
                        >
                          <Copy size={16} />
                        </button>
                        <button
                          onClick={() => handleToggleNote(msg)}
                          className={`p-1.5 rounded-md transition-colors group relative ${msg.is_saved ? "text-indigo-600 bg-indigo-50" : "hover:bg-gray-100 hover:text-indigo-600"}`}
                          title={
                            msg.is_saved ? "Remove from Notes" : "Save to Notes"
                          }
                        >
                          <BookmarkPlus
                            size={16}
                            className={msg.is_saved ? "fill-current" : ""}
                          />
                        </button>
                        <button
                          onClick={() => shareResponse(msg.content)}
                          className="p-1.5 hover:bg-gray-100 hover:text-emerald-600 rounded-md transition-colors group relative"
                          title="Share Message"
                        >
                          <Share2 size={16} />
                        </button>
                      </div>
                    )}
                  </div>

                  {msg.role === "user" && (
                    <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center text-gray-600 shrink-0 mt-1">
                      <User size={18} />
                    </div>
                  )}
                </div>
              ))
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>

        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-white via-white to-transparent pt-10 pb-6 px-4 sm:px-8">
          <form
            onSubmit={handleSend}
            className="max-w-3xl mx-auto relative flex items-end gap-2 bg-white border border-gray-300 rounded-2xl shadow-lg p-2 focus-within:ring-2 focus-within:ring-indigo-500 focus-within:border-transparent transition-all"
          >
            <textarea
              className="w-full max-h-32 bg-transparent border-none focus:ring-0 resize-none py-3 pl-4 pr-12 text-gray-900 placeholder-gray-500 outline-none"
              placeholder="Message your agent..."
              rows="1"
              value={input}
              onChange={(e) => {
                setInput(e.target.value);
                e.target.style.height = "auto";
                e.target.style.height = e.target.scrollHeight + "px";
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend(e);
                }
              }}
            />
            <button
              type="submit"
              disabled={!input.trim() || isTyping}
              className="absolute right-4 bottom-3 p-2 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 disabled:bg-gray-300 disabled:text-gray-500 transition-all shadow-sm"
            >
              {isTyping ? (
                <Loader2 size={18} className="animate-spin" />
              ) : (
                <Send size={18} />
              )}
            </button>
          </form>
          <div className="text-center mt-3 text-xs text-gray-400 font-medium">
            RagMate AI can make mistakes. Consider verifying important
            information.
          </div>
        </div>
      </div>

      {/* ========================================== */}
      {/* 🔥 NOTES MODAL WITH NATIVE PDF EXPORT */}
      {/* ========================================== */}
      {isNotesModalOpen && (
        <div className="fixed inset-0 bg-gray-900/60 backdrop-blur-sm flex items-center justify-end z-50">
          <div className="bg-white w-full max-w-md h-full shadow-2xl flex flex-col animate-in slide-in-from-right">
            <div className="p-6 border-b border-gray-200 flex items-center justify-between bg-gray-50 print:hidden">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-indigo-100 text-indigo-600 rounded-lg">
                  <BookmarkPlus size={24} />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-gray-900">
                    Saved Notes
                  </h2>
                  <p className="text-sm text-gray-500">
                    {savedNotesDB.length} pinned items
                  </p>
                </div>
              </div>
              <button
                onClick={() => setIsNotesModalOpen(false)}
                className="p-2 text-gray-400 hover:text-gray-700 hover:bg-gray-200 rounded-full transition-colors"
              >
                <XIcon size={24} />
              </button>
            </div>

            <div
              ref={allNotesPrintRef}
              className="flex-1 overflow-y-auto p-6 space-y-6 bg-gray-50/50 print:bg-white print:p-8"
            >
              <div className="hidden print:block mb-6">
                <h1 className="text-2xl font-bold text-indigo-600">
                  RagMate AI - Saved Notes
                </h1>
                <p className="text-sm text-gray-500">
                  Generated on {new Date().toLocaleString()}
                </p>
                <hr className="mt-4 border-gray-200" />
              </div>

              {savedNotesDB.length === 0 ? (
                <div className="text-center py-20 text-gray-400 print:hidden">
                  <BookmarkPlus size={48} className="mx-auto mb-4 opacity-50" />
                  <p>No notes saved yet.</p>
                </div>
              ) : (
                savedNotesDB.map((note, index) => (
                  <SingleNoteItem
                    key={note.id}
                    note={note}
                    index={index}
                    onRemove={(id) =>
                      toggleNoteMutation.mutate({
                        messageId: id,
                        isSaved: false,
                      })
                    }
                  />
                ))
              )}
            </div>

            <div className="p-6 border-t border-gray-200 bg-white print:hidden">
              <button
                onClick={handlePrintAllNotes}
                disabled={savedNotesDB.length === 0}
                className="w-full flex justify-center items-center gap-2 py-3.5 px-4 rounded-xl text-base font-semibold text-white bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-300 disabled:text-gray-500 transition-all shadow-md hover:shadow-lg disabled:shadow-none"
              >
                <Download size={18} /> Export All Notes as PDF
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
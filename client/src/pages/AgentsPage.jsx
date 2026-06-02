import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import {
  Bot,
  Plus,
  MessageSquare,
  Database,
  MoreHorizontal,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useAgents } from "../hooks/useAgents";
import EmptyState from "../components/shared/EmptyState";
import LoadingSkeleton from "../components/shared/LoadingSkeleton";
import { useUIStore } from "../store/useUIStore";

function formatCreatedAt(value) {
  if (!value) return "Not available";

  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(value));
}

export default function AgentsPage() {
  const setCreateAgentWizardOpen = useUIStore(
    (state) => state.setCreateAgentWizardOpen,
  );

  const { user } = useAuth();

  const {
    data: agents = [],
    isError,
    isLoading,
    error,
  } = useAgents(user?.id);

  if (isLoading) {
    return (
      <div className="p-10">
        <LoadingSkeleton />
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-10">
        <div>
          <h1 className="text-4xl font-bold text-slate-900">AI Agents</h1>

          <p className="text-slate-500 mt-2">
            Build and manage custom RAG assistants.
          </p>
        </div>

        <button
          onClick={() => setCreateAgentWizardOpen(true)}
          className="
            flex
            items-center
            gap-2
            px-5
            py-3
            rounded-2xl
            bg-indigo-600
            text-white
            hover:bg-indigo-700
            transition-all
          "
        >
          <Plus size={18} />
          Create Agent
        </button>
      </div>

      {isError && (
        <div className="mb-6 rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
          {error?.message ||
            "Unable to load agents. Please try again."}
        </div>
      )}

      {agents.length === 0 && !isError ? (
        <EmptyState
          title="No agents yet"
          description="Create your first AI agent to connect models, instructions, and knowledge settings."
          action={
            <button
              onClick={() => setCreateAgentWizardOpen(true)}
              className="
                flex
                items-center
                gap-2
                px-5
                py-3
                rounded-2xl
                bg-indigo-600
                text-white
                hover:bg-indigo-700
                transition-all
              "
            >
              <Plus size={18} />
              Create Agent
            </button>
          }
        />
      ) : (
        <div className="grid lg:grid-cols-3 gap-6">
          {agents.map((agent) => (
            <motion.div
              key={agent.id}
              whileHover={{
                y: -4,
              }}
              className="
              bg-white
              rounded-3xl
              border
              border-slate-200
              p-6
              shadow-sm
              hover:shadow-xl
              transition-all
            "
            >
              <div className="flex items-start justify-between">
                <div className="h-14 w-14 rounded-2xl bg-indigo-100 flex items-center justify-center">
                  <Bot className="text-indigo-600" />
                </div>

                <button className="p-2 rounded-xl hover:bg-slate-100">
                  <MoreHorizontal size={18} />
                </button>
              </div>

              <h3 className="font-semibold text-lg mt-5">
                {agent.name}
              </h3>

              {agent.description && (
                <p className="mt-2 text-sm text-slate-500 line-clamp-2">
                  {agent.description}
                </p>
              )}

              <div className="flex flex-wrap gap-2 mt-4">
                <span className="px-3 py-1 rounded-full bg-indigo-50 text-indigo-600 text-xs font-medium">
                  {agent.provider}
                </span>

                <span className="px-3 py-1 rounded-full bg-slate-100 text-slate-700 text-xs font-medium">
                  {agent.model}
                </span>
              </div>

              <div className="mt-5 space-y-2">
                <div className="flex justify-between gap-4 text-sm">
                  <span className="text-slate-500">Embedding</span>

                  <span className="text-right">
                    {agent.embedding_model}
                  </span>
                </div>

                <div className="flex justify-between gap-4 text-sm">
                  <span className="text-slate-500">Chunking</span>

                  <span className="text-right">
                    {agent.chunk_strategy}
                  </span>
                </div>

                <div className="flex justify-between gap-4 text-sm">
                  <span className="text-slate-500">Created</span>

                  <span className="text-right">
                    {formatCreatedAt(agent.created_at)}
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 mt-6">
                <Link
                  to="/knowledge"
                  className="
                  flex
                  items-center
                  justify-center
                  gap-2
                  py-3
                  rounded-2xl
                  border
                  border-slate-200
                  hover:bg-slate-50
                "
                >
                  <Database size={16} />
                  Knowledge
                </Link>

                <Link
                  to="/chat"
                  className="
                  flex
                  items-center
                  justify-center
                  gap-2
                  py-3
                  rounded-2xl
                  bg-indigo-600
                  text-white
                "
                >
                  <MessageSquare size={16} />
                  Chat
                </Link>
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}

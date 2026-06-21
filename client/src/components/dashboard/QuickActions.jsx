import { UploadCloud, MessageSquare, Bot, ArrowUpRight } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useWorkspacePermissions } from "../../hooks/useSettings";

export default function QuickActions({ onCreateAgent }) {
  const navigate = useNavigate();
  const { canManageAgents } = useWorkspacePermissions();

  const actions = [
    {
      icon: Bot,
      label: "Go to Playground",
      description: "Manage & configure agents",
      color: "from-blue-500/10 to-indigo-500/10 text-blue-500 border-blue-500/20",
      action: () => navigate("/playground"),
    },
    {
      icon: UploadCloud,
      label: "Upload Data",
      description: "Index files into knowledge base",
      color: "from-emerald-500/10 to-teal-500/10 text-emerald-500 border-emerald-500/20",
      action: () => navigate("/knowledge"),
    },
    {
      icon: MessageSquare,
      label: "Start Chat",
      description: "Interact with assistants live",
      color: "from-purple-500/10 to-pink-500/10 text-purple-500 border-purple-500/20",
      action: () => navigate("/chat"),
    },
  ];

  return (
    <div
      className="
        glass-card
        p-6
      "
    >
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="font-bold text-lg text-foreground">Quick Shortcuts</h3>
          <p className="text-xs text-muted-foreground mt-0.5">Frequent actions & routing</p>
        </div>
        <span className="text-xs font-semibold bg-primary/10 text-primary px-3 py-1 rounded-full">
          Productivity
        </span>
      </div>

      <div className="grid grid-cols-1 gap-3">
        {actions.map((action) => (
          <button
            key={action.label}
            onClick={action.action}
            className="
              group
              cursor-pointer
              relative
              overflow-hidden
              flex
              items-center
              gap-4
              p-4
              rounded-2xl
              border
              border-border/60
              hover:border-primary/30
              bg-muted/10
              hover:bg-muted/30
              transition-all
              duration-200
              text-left
              hover:-translate-y-0.5
              hover:shadow-md
            "
          >
            {/* Background Accent Glow */}
            <div className={`absolute -right-6 -bottom-6 w-16 h-16 rounded-full blur-xl opacity-0 group-hover:opacity-20 bg-gradient-to-r ${action.color.split(' ')[0]} to-transparent transition-opacity`} />

            <div
              className={`
                h-11
                w-11
                rounded-xl
                bg-gradient-to-br
                ${action.color.split(' ').slice(0, 2).join(' ')}
                ${action.color.split(' ').slice(2).join(' ')}
                flex
                items-center
                justify-center
                group-hover:scale-105
                transition-transform
                shrink-0
              `}
            >
              <action.icon size={20} />
            </div>

            <div className="flex-1 min-w-0 pr-6">
              <span className="block font-semibold text-sm text-foreground">{action.label}</span>
              <span className="block text-xs text-muted-foreground truncate mt-0.5">{action.description}</span>
            </div>

            <div className="absolute right-4 top-4 text-muted-foreground/45 group-hover:text-primary group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-all">
              <ArrowUpRight size={14} />
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}


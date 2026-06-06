import { Plus, UploadCloud, MessageSquare, FileText, Bot } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useWorkspacePermissions } from "../../hooks/useSettings";

export default function QuickActions({ onCreateAgent }) {
  const navigate = useNavigate();
  const { canManageAgents } = useWorkspacePermissions();

  const actions = [
    ...(canManageAgents ? [{
      icon: Plus,
      label: "Create Agent",
      action: () => {
        if (onCreateAgent) {
          onCreateAgent();
        } else {
          navigate("/agents");
        }
      },
    }] : []),
    {
      icon: Bot,
      label: "View Agents",
      action: () => navigate("/agents"),
    },
    {
      icon: UploadCloud,
      label: "Upload Data",
      action: () => navigate("/knowledge"),
    },
    {
      icon: MessageSquare,
      label: "Start Chat",
      action: () => navigate("/chat"),
    },
    {
      icon: FileText,
      label: "Open Notes",
      action: () => navigate("/notes"),
    },
  ];

  return (
    <div
      className="
   glass-card
   p-6
 "
    >
      {" "}
      <div className="flex items-center justify-between mb-6">
        {" "}
        <h3 className="font-semibold text-lg text-foreground">Quick Actions </h3>
        <span className="text-xs text-muted-foreground">Productivity</span>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {actions.map((action) => (
          <button
            key={action.label}
            onClick={action.action}
            className="
        group
        cursor-pointer
        flex
        flex-col
        items-center
        justify-center
        gap-3
        h-32
        rounded-3xl
        border
        border-border
        hover:border-primary/40
        hover:bg-primary/5
        bg-background/50
        text-foreground
        transition-all
        duration-200
        hover:-translate-y-1
        hover:shadow-lg
      "
          >
            <div
              className="
          h-12
          w-12
          rounded-2xl
          bg-primary/10
          text-primary
          flex
          items-center
          justify-center
          group-hover:scale-110
          transition-transform
        "
            >
              <action.icon size={22} />
            </div>

            <span className="font-medium text-sm">{action.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

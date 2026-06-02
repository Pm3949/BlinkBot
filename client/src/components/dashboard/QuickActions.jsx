import { Plus, UploadCloud, MessageSquare, FileText, Bot } from "lucide-react";

import { useNavigate } from "react-router-dom";

export default function QuickActions({ onCreateAgent }) {
  const navigate = useNavigate();

  const actions = [
    {
      icon: Plus,
      label: "Create Agent",
      action: () => {
        if (onCreateAgent) {
          onCreateAgent();
        } else {
          navigate("/agents");
        }
      },
    },
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
   bg-white
   dark:bg-zinc-900
   rounded-2xl
   border
   border-slate-200
   dark:border-zinc-800
   p-6
   shadow-sm
 "
    >
      {" "}
      <div className="flex items-center justify-between mb-6">
        {" "}
        <h3 className="font-semibold text-lg">Quick Actions </h3>
        <span className="text-xs text-slate-500 dark:text-zinc-400">Productivity</span>
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
        border-slate-200
        dark:border-zinc-800
        hover:border-indigo-300
        hover:bg-indigo-50
        dark:hover:bg-zinc-800
        dark:bg-zinc-950/40
        text-slate-800
        dark:text-zinc-100
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
          bg-indigo-100
          dark:bg-indigo-500/15
          text-indigo-600
          dark:text-indigo-300
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

import {
  LayoutDashboard,
  Bot,
  Database,
  MessageSquare,
  BookOpen,
  BarChart3,
  Settings,
  LogOut,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";
import { NavLink } from "react-router-dom";
import { toast } from "sonner";
import Logo from "../shared/Logo";
import { signOut } from "../../services/authService";
import { useUIStore } from "../../store/useUIStore";

const groups = [
  {
    label: "Workspace",
    items: [
      {
        label: "Dashboard",
        icon: LayoutDashboard,
        path: "/",
      },
      {
        label: "Agents",
        icon: Bot,
        path: "/agents",
      },
      {
        label: "Knowledge",
        icon: Database,
        path: "/knowledge",
      },
    ],
  },
  {
    label: "AI Work",
    items: [
      {
        label: "Chat",
        icon: MessageSquare,
        path: "/chat",
      },
      {
        label: "Notes",
        icon: BookOpen,
        path: "/notes",
      },
      {
        label: "Analytics",
        icon: BarChart3,
        path: "/analytics",
      },
    ],
  },
  {
    label: "System",
    items: [
      {
        label: "Settings",
        icon: Settings,
        path: "/settings",
      },
    ],
  },
];

export default function AppSidebar({ onNavigate, forceExpanded = false }) {
  const storedCollapsed = useUIStore((state) => state.sidebarCollapsed);
  const toggleCollapsed = useUIStore((state) => state.toggleSidebarCollapsed);
  const collapsed = forceExpanded ? false : storedCollapsed;

  const handleSignOut = async () => {
    try {
      await signOut();
      toast.success("Signed out");
      onNavigate?.();
    } catch (error) {
      toast.error(error.message || "Unable to sign out. Please try again.");
    }
  };

  return (
    <aside
      className={`fixed left-0 top-0 z-50 flex h-screen flex-col border-r border-slate-200/80 bg-white/90 shadow-sm backdrop-blur-xl transition-[width] duration-300 ease-out dark:border-zinc-800/80 dark:bg-zinc-950/88 ${
        collapsed ? "w-[76px]" : "w-[264px]"
      }`}
    >
      <div className="flex h-20 items-center justify-between border-b border-slate-200/80 px-4 dark:border-zinc-800">
        <div className={`min-w-0 transition-opacity ${collapsed ? "opacity-0" : "opacity-100"}`}>
          {!collapsed && <Logo />}
        </div>

        <button
          type="button"
          onClick={toggleCollapsed}
          disabled={forceExpanded}
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-slate-200 text-slate-500 transition hover:bg-slate-100 hover:text-slate-950 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 dark:border-zinc-800 dark:text-zinc-400 dark:hover:bg-zinc-900 dark:hover:text-zinc-50"
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
        </button>
      </div>

      <nav className="flex-1 space-y-6 overflow-y-auto overflow-x-hidden px-3 py-5">
        {groups.map((group) => (
          <div key={group.label}>
            {!collapsed && (
              <div className="mb-2 px-3 text-[11px] font-semibold uppercase tracking-wide text-slate-400 dark:text-zinc-500">
                {group.label}
              </div>
            )}

            <div className="space-y-1">
              {group.items.map((item) => (
                <NavLink
                  key={item.label}
                  to={item.path}
                  end={item.path === "/"}
                  onClick={onNavigate}
                  title={collapsed ? item.label : undefined}
                  className={({ isActive }) => `
                    group relative flex h-11 items-center gap-3 rounded-xl px-3 text-sm font-medium transition-all duration-200
                    focus:outline-none focus:ring-2 focus:ring-indigo-500/30
                    ${
                      isActive
                        ? "bg-indigo-50 text-indigo-700 shadow-sm dark:bg-indigo-500/15 dark:text-indigo-300"
                        : "text-slate-600 hover:bg-slate-100 hover:text-slate-950 dark:text-zinc-400 dark:hover:bg-zinc-900 dark:hover:text-zinc-50"
                    }
                    ${collapsed ? "justify-center" : ""}
                  `}
                >
                  {({ isActive }) => (
                    <>
                      <span
                        className={`absolute left-0 h-6 w-1 rounded-r-full bg-indigo-600 transition-opacity dark:bg-indigo-400 ${
                          isActive ? "opacity-100" : "opacity-0"
                        }`}
                      />

                      <item.icon size={18} className="shrink-0" />

                      {!collapsed && <span className="truncate">{item.label}</span>}
                    </>
                  )}
                </NavLink>
              ))}
            </div>
          </div>
        ))}
      </nav>

      <div className="border-t border-slate-200/80 p-3 dark:border-zinc-800">
        {!collapsed && (
          <div className="mb-3 rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-zinc-800 dark:bg-zinc-900/70">
            <div className="text-sm font-semibold text-slate-900 dark:text-zinc-50">
              Personal Workspace
            </div>

            <div className="mt-1 text-xs text-slate-500 dark:text-zinc-400">
              Free Plan
            </div>
          </div>
        )}

        <button
          type="button"
          onClick={handleSignOut}
          title={collapsed ? "Logout" : undefined}
          className={`flex h-11 w-full items-center gap-3 rounded-xl px-3 text-sm font-medium text-slate-600 transition hover:bg-red-50 hover:text-red-600 focus:outline-none focus:ring-2 focus:ring-red-500/20 dark:text-zinc-400 dark:hover:bg-red-500/10 dark:hover:text-red-300 ${
            collapsed ? "justify-center" : ""
          }`}
        >
          <LogOut size={18} />
          {!collapsed && <span>Logout</span>}
        </button>
      </div>
    </aside>
  );
}

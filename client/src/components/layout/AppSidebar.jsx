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
  Users,
  CreditCard,
  ChevronDown,
  Globe,
  ShieldCheck
} from "lucide-react";
import { useEffect } from "react";
import { useUserWorkspaces, useWorkspacePermissions } from "../../hooks/useSettings";
import { NavLink } from "react-router-dom";
import { toast } from "sonner";
import Logo from "../shared/Logo";
import { signOut } from "../../services/authService";
import { useUIStore } from "../../store/useUIStore";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";

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
        label: "Chatbots",
        icon: Globe,
        path: "/chatbots",
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
        label: "Team",
        icon: Users,
        path: "/team",
      },
      {
        label: "Billing",
        icon: CreditCard,
        path: "/billing",
      },
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
  const activeWorkspaceId = useUIStore((state) => state.activeWorkspaceId);
  const setActiveWorkspaceId = useUIStore((state) => state.setActiveWorkspaceId);
  
  const { data: workspaces = [], isLoading } = useUserWorkspaces();
  const activeWorkspace = workspaces.find((w) => w.id === activeWorkspaceId) || workspaces[0];
  const { isAdmin } = useWorkspacePermissions();

  useEffect(() => {
    if (workspaces.length > 0 && !activeWorkspaceId) {
      setActiveWorkspaceId(workspaces[0].id);
    }
  }, [workspaces, activeWorkspaceId, setActiveWorkspaceId]);

  const handleSignOut = async () => {
    try {
      await signOut();
      toast.success("Signed out");
      onNavigate?.();
    } catch (error) {
      toast.error(error.message || "Unable to sign out. Please try again.");
    }
  };

  const filteredGroups = groups.map(group => {
  if (group.label === "System") {
    return {
      ...group,
      items: group.items.filter(item => {
        // केवल Admin ही Team और Billing देख सकते हैं
        if (item.path === "/team" || item.path === "/billing") {
          return isAdmin;
        }
        return true;
      })
    };
  }
  return group;
});

  return (
    <aside
      className={`fixed left-0 top-0 z-50 flex h-screen flex-col border-r border-border glass shadow-sm transition-[width] duration-300 ease-out ${
        collapsed ? "w-[76px]" : "w-[264px]"
      }`}
    >
      <div className="flex h-20 items-center justify-between border-b border-border px-4">
        <div className={`min-w-0 transition-opacity ${collapsed ? "opacity-0" : "opacity-100"}`}>
          {!collapsed && <Logo />}
        </div>

        <button
          type="button"
          onClick={toggleCollapsed}
          disabled={forceExpanded}
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-border text-muted-foreground transition hover:bg-muted hover:text-foreground focus:outline-none focus:ring-2 focus:ring-primary/30"
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
        </button>
      </div>

      <nav className="flex-1 space-y-6 overflow-y-auto overflow-x-hidden px-3 py-5">
        {filteredGroups.map((group) => (
          <div key={group.label}>
            {!collapsed && (
              <div className="mb-2 px-3 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
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
                    focus:outline-none focus:ring-2 focus:ring-primary/30
                    ${
                      isActive
                        ? "bg-primary/10 text-primary shadow-sm"
                        : "text-muted-foreground hover:bg-muted hover:text-foreground"
                    }
                    ${collapsed ? "justify-center" : ""}
                  `}
                >
                  {({ isActive }) => (
                    <>
                      <span
                        className={`absolute left-0 h-6 w-1 rounded-r-full bg-primary transition-opacity ${
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

      <div className="border-t border-border p-3">
        {!collapsed && (
          <div className="mb-3 rounded-2xl border border-border bg-background/50 p-3 backdrop-blur-md relative">
            <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-1.5 px-1">
              Active Workspace
            </div>
            
            {isLoading ? (
              <div className="h-10 animate-pulse bg-muted rounded-xl"></div>
            ) : (
              <Select
                value={activeWorkspaceId || ""}
                onValueChange={(value) => setActiveWorkspaceId(value)}
              >
                <SelectTrigger className="w-full h-10 border-0 bg-transparent shadow-none hover:bg-muted/50 font-semibold focus:ring-1">
                  <SelectValue placeholder="Select Workspace" />
                </SelectTrigger>
                <SelectContent>
                  {workspaces.map((ws) => (
                    <SelectItem key={ws.id} value={ws.id}>
                      {ws.name} ({ws.role})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>
        )}

        <button
          type="button"
          onClick={handleSignOut}
          title={collapsed ? "Logout" : undefined}
          className={`flex h-11 w-full items-center gap-3 rounded-xl px-3 text-sm font-medium text-muted-foreground transition hover:bg-red-500/10 hover:text-red-600 focus:outline-none focus:ring-2 focus:ring-red-500/20 ${
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

import { useEffect } from "react";
import { Outlet } from "react-router-dom";
import AppSidebar from "../components/layout/AppSidebar";
import CommandPalette from "../components/layout/CommandPalette";
import AppHeader from "../components/layout/AppHeader";
import MobileSidebar from "../components/layout/MobileSidebar";
import CreateAgentWizard from "../components/agents/CreateAgentWizard";
import { useUIStore } from "../store/useUIStore";
import { usePermissionSync } from "../hooks/usePermissionSync";

export default function AppShell() {
  const darkMode = useUIStore((state) => state.darkMode);
  const setSidebarOpen = useUIStore((state) => state.setSidebarOpen);
  const sidebarCollapsed = useUIStore((state) => state.sidebarCollapsed);
  const createAgentWizardOpen = useUIStore(
    (state) => state.createAgentWizardOpen,
  );
  const setCreateAgentWizardOpen = useUIStore(
    (state) => state.setCreateAgentWizardOpen,
  );

  // Real-time: Admin द्वारा permission बदलने पर तुरंत UI update
  usePermissionSync();

  useEffect(() => {
    document.documentElement.classList.toggle("dark", darkMode);
  }, [darkMode]);

  return (
    <>
      <CommandPalette />
      <MobileSidebar />
      {createAgentWizardOpen && (
        <CreateAgentWizard onClose={() => setCreateAgentWizardOpen(false)} />
      )}

      {/*
        CSS-variable layout: --sidebar-width is set once here and used by
        both the sidebar (width) and the main content (margin-left).
        This guarantees zero gap at every animation frame.
      */}
      <div
        className="min-h-screen bg-background text-foreground transition-colors"
        style={{
          "--sidebar-width": sidebarCollapsed ? "76px" : "264px",
        }}
      >
        <div className="hidden lg:block">
          <AppSidebar />
        </div>

        <div
          className="flex min-h-screen flex-col"
          style={{
            marginLeft: "var(--sidebar-width, 0px)",
            transition: "margin-left 300ms cubic-bezier(0.4, 0, 0.2, 1)",
          }}
        >
          <AppHeader onMenuClick={() => setSidebarOpen(true)} />

          <main className="flex-1 overflow-y-auto px-4 py-6 sm:px-6 lg:px-8">
            <div className="w-full">
              <Outlet />
            </div>
          </main>
        </div>
      </div>
    </>
  );
}

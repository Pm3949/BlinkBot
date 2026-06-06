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

      <div className="min-h-screen bg-background text-foreground transition-colors">
        <div className="hidden lg:block">
          <AppSidebar />
        </div>

        <div
          className={`flex min-h-screen flex-col transition-[margin] duration-300 ease-out ${
            sidebarCollapsed ? "lg:ml-[76px]" : "lg:ml-[264px]"
          }`}
        >
          <AppHeader
            onMenuClick={() => setSidebarOpen(true)}
          />

          <main className="flex-1 overflow-y-auto px-4 py-6 sm:px-6 lg:px-8">
            <div className="mx-auto w-full max-w-[1500px]">
              <Outlet />
            </div>
          </main>
        </div>
      </div>
    </>
  );
}

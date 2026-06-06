import AppSidebar from "./AppSidebar";
import { useUIStore } from "../../store/useUIStore";

export default function MobileSidebar() {
  const sidebarOpen = useUIStore((state) => state.sidebarOpen);
  const setSidebarOpen = useUIStore((state) => state.setSidebarOpen);

  if (!sidebarOpen) return null;

  return (
    <div className="fixed inset-0 z-[90] lg:hidden">
      <button
        aria-label="Close navigation"
        className="absolute inset-0 bg-slate-950/40 backdrop-blur-sm"
        onClick={() => setSidebarOpen(false)}
      />

      <div className="absolute left-0 top-0 h-full w-[264px] shadow-2xl">
        <AppSidebar
          forceExpanded
          onNavigate={() => setSidebarOpen(false)}
        />
      </div>
    </div>
  );
}

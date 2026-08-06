import { create } from "zustand";
import { persist } from "zustand/middleware";
import { encodeId, decodeId } from "../lib/idCrypt";

// ── Custom storage adapter that encodes/decodes the workspaceId ──
const encryptedStorage = {
  getItem: (name) => {
    const raw = localStorage.getItem(name);
    if (!raw) return null;
    try {
      const parsed = JSON.parse(raw);
      // Decode the persisted (obfuscated) workspace id back to a plain UUID
      if (parsed?.state?.activeWorkspaceId) {
        parsed.state.activeWorkspaceId = decodeId(parsed.state.activeWorkspaceId);
      }
      return JSON.stringify(parsed);
    } catch {
      return raw;
    }
  },
  setItem: (name, value) => {
    try {
      const parsed = JSON.parse(value);
      // Encode the workspace id before writing to localStorage
      if (parsed?.state?.activeWorkspaceId) {
        parsed.state.activeWorkspaceId = encodeId(parsed.state.activeWorkspaceId);
      }
      localStorage.setItem(name, JSON.stringify(parsed));
    } catch {
      localStorage.setItem(name, value);
    }
  },
  removeItem: (name) => localStorage.removeItem(name),
};

export const useUIStore = create(
  persist(
    (set) => ({
      sidebarOpen: false,

      sidebarCollapsed: false,

      commandPaletteOpen: false,

      notesDrawerOpen: false,

      darkMode: true,

      createAgentWizardOpen: false,

      activeWorkspaceId: null,

      setSidebarOpen: (value) =>
        set({
          sidebarOpen: value,
        }),

      setSidebarCollapsed: (value) =>
        set({
          sidebarCollapsed: value,
        }),

      toggleSidebarCollapsed: () =>
        set((state) => ({
          sidebarCollapsed: !state.sidebarCollapsed,
        })),

      setCommandPaletteOpen: (value) =>
        set({
          commandPaletteOpen: value,
        }),

      setNotesDrawerOpen: (value) =>
        set({
          notesDrawerOpen: value,
        }),

      setCreateAgentWizardOpen: (value) =>
        set({
          createAgentWizardOpen: value,
        }),

      setDarkMode: (value) => {
        if (typeof document !== 'undefined') {
          if (value) document.documentElement.classList.add("dark");
          else document.documentElement.classList.remove("dark");
        }
        set({ darkMode: value });
      },

      toggleDarkMode: () =>
        set((state) => {
          const newValue = !state.darkMode;
          if (typeof document !== 'undefined') {
            if (newValue) document.documentElement.classList.add("dark");
            else document.documentElement.classList.remove("dark");
          }
          return { darkMode: newValue };
        }),

      setActiveWorkspaceId: (id) => set({ activeWorkspaceId: id }),

      tools: [],
      storeTemplates: [],
      loadingTools: false,
      
      setTools: (tools) => set({ tools }),
      setStoreTemplates: (storeTemplates) => set({ storeTemplates }),
      setLoadingTools: (loadingTools) => set({ loadingTools }),

      fetchTools: async (workspaceId) => {
        if (!workspaceId) return;
        set({ loadingTools: true });
        try {
          const { getWorkspaceTools } = await import("../services/workspaceToolsService");
          const data = await getWorkspaceTools(workspaceId);
          set({ tools: data });
        } catch (e) {
          console.error("Failed to load tools in store:", e);
        } finally {
          set({ loadingTools: false });
        }
      },
      
      fetchStoreTemplates: async () => {
        try {
          const API_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
          const { getAuthHeaders } = await import("../lib/api");
          const headers = getAuthHeaders();
          
          const [templatesRes, globalsRes, predefinedRes] = await Promise.all([
            fetch(`${API_URL}/api/tools/templates`, { headers }),
            fetch(`${API_URL}/api/tools/global-registry`, { headers }),
            fetch(`${API_URL}/api/tools/pre-defined`, { headers })
          ]);
          
          const templates = await templatesRes.json();
          const globals = await globalsRes.json();
          const predefined = await predefinedRes.json();
          
          const formattedPredefined = predefined.map(p => ({
            id: p.tool_key,
            name: p.name,
            tool_type: "api_webhook",
            description: p.description,
            category: p.category,
            requires_auth: p.requires_auth,
            is_predefined: true,
            tool_key: p.tool_key
          }));
          
          set({ storeTemplates: [...globals, ...formattedPredefined, ...templates] });
        } catch (err) {
          console.error("Failed to load store templates in store:", err);
        }
      },
    }),
    {
      name: "blinkbot-ui",
      storage: encryptedStorage,
      partialize: (state) => ({
        darkMode: state.darkMode,
        sidebarCollapsed: state.sidebarCollapsed,
        activeWorkspaceId: state.activeWorkspaceId,
      }),
    },
  ),
);

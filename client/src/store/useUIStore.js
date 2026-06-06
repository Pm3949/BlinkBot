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

      darkMode: false,

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
    }),
    {
      name: "ragmate-ui",
      storage: encryptedStorage,
      partialize: (state) => ({
        darkMode: state.darkMode,
        sidebarCollapsed: state.sidebarCollapsed,
        activeWorkspaceId: state.activeWorkspaceId,
      }),
    },
  ),
);

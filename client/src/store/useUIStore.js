import { create } from "zustand";
import { persist } from "zustand/middleware";

export const useUIStore = create(
  persist(
    (set) => ({
      sidebarOpen: false,

      sidebarCollapsed: false,

      commandPaletteOpen: false,

      notesDrawerOpen: false,

      darkMode: false,

      createAgentWizardOpen: false,

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

      setDarkMode: (value) =>
        set({
          darkMode: value,
        }),

      toggleDarkMode: () =>
        set((state) => ({
          darkMode: !state.darkMode,
        })),
    }),
    {
      name: "ragmate-ui",
      partialize: (state) => ({
        darkMode: state.darkMode,
        sidebarCollapsed: state.sidebarCollapsed,
      }),
    },
  ),
);

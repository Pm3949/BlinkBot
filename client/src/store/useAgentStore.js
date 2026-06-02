import { create } from "zustand";

export const useAgentStore = create((set) => ({
  agents: [],
  activeAgent: null,

  setAgents: (agents) =>
    set({
      agents,
    }),

  setActiveAgent: (agent) =>
    set({
      activeAgent: agent,
    }),

  addAgent: (agent) =>
    set((state) => ({
      agents: [
        agent,
        ...state.agents,
      ],
    })),

  removeAgent: (id) =>
    set((state) => ({
      agents: state.agents.filter(
        (a) => a.id !== id
      ),
    })),
}));
import { create } from 'zustand';

export const useTraceStore = create((set) => ({
  steps: [],
  isRawMode: false,
  addStep: (step) => set((state) => ({ 
    steps: [...state.steps, { 
      id: Math.random().toString(36).substring(7),
      timestamp: new Date().toLocaleTimeString(),
      ...step 
    }] 
  })),
  clearSteps: () => set({ steps: [] }),
  setRawMode: (isRawMode) => set({ isRawMode: isRawMode }),
}));

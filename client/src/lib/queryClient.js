import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // ─── Cache duration ────────────────────────────────────────────────────
      staleTime: 1000 * 60 * 2,   // 2 min: data treated as fresh (no refetch)
      gcTime:    1000 * 60 * 10,  // 10 min: keep unused data in memory

      // ─── Refetch triggers — disable unnecessary ones ───────────────────────
      refetchOnWindowFocus:   false, // don't refetch when user switches tabs
      refetchOnReconnect:     false, // don't refetch on network reconnect
      refetchOnMount:         true,  // still fetch when component first mounts

      // ─── Error handling ────────────────────────────────────────────────────
      retry: 1, // only retry once on failure
    },
  },
});


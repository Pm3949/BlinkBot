import { useQuery } from "@tanstack/react-query";
import { getAnalytics } from "../services/analyticsService";

export function useAnalytics() {
  return useQuery({
    queryKey: ["analytics"],
    queryFn: getAnalytics,
    staleTime: 1000 * 60 * 5, // 5 min — analytics are aggregated, not real-time
  });
}


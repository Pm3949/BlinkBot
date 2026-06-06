import { useQuery } from "@tanstack/react-query";
import { getAnalytics } from "../services/analyticsService";

export function useAnalytics() {
  return useQuery({
    queryKey: ["analytics"],
    queryFn: getAnalytics,
  });
}

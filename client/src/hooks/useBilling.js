import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getSubscription, createRazorpayOrder } from "../services/billingService";

export function useSubscription() {
  return useQuery({
    queryKey: ["subscription"],
    queryFn: getSubscription,
  });
}

export function useCreateRazorpayOrder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ planTier, billingCycle, limits }) => createRazorpayOrder(planTier, billingCycle, limits),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["subscription"] });
    },
  });
}

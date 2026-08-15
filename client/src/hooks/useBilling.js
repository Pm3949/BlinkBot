import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getSubscription, createRazorpayOrder, getWallet, getInvoices, rechargeWallet, updateRechargeSettings } from "../services/billingService";

export function useSubscription() {
  return useQuery({
    queryKey: ["subscription"],
    queryFn: getSubscription,
  });
}

export function useInvoices() {
  return useQuery({
    queryKey: ["invoices"],
    queryFn: getInvoices,
  });
}

export function useCreateRazorpayOrder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ planTier, billingCycle, limits }) => createRazorpayOrder(planTier, billingCycle, limits),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["subscription"] });
      queryClient.invalidateQueries({ queryKey: ["invoices"] });
    },
  });
}

export function useWallet() {
  return useQuery({
    queryKey: ["wallet"],
    queryFn: getWallet,
  });
}

export function useRechargeWallet() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (credits) => rechargeWallet(credits),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["wallet"] });
      queryClient.invalidateQueries({ queryKey: ["invoices"] });
    },
  });
}

export function useUpdateRechargeSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ enabled, threshold, amount_usd }) => updateRechargeSettings(enabled, threshold, amount_usd),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["wallet"] });
    },
  });
}


/**
 * TanStack Query hooks, one per endpoint. Add each hook alongside the feature that needs it
 * (CHECKLIST I-10).
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "./client";
import type {
  BudgetStatus,
  HealthStatus,
  InvestorProfile,
  InvestorProfileIn,
  PipelineRun,
  ProfileOptions,
} from "./types";

export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: () => apiFetch<HealthStatus>("/health"),
    staleTime: 60_000,
  });
}

/** SerpApi searches used this month (our ledger) and left on the account (free Account API). */
export function useBudget() {
  return useQuery({
    queryKey: ["budget"],
    queryFn: () => apiFetch<BudgetStatus>("/meta/budget"),
    staleTime: 60_000,
  });
}

// --- Investor profiles (F-01) ----------------------------------------------------------

/** Choices for the profile form. Static reference data, so it never goes stale. */
export function useProfileOptions() {
  return useQuery({
    queryKey: ["profile-options"],
    queryFn: () => apiFetch<ProfileOptions>("/meta/profile-options"),
    staleTime: Infinity,
  });
}

export function useProfiles() {
  return useQuery({
    queryKey: ["profiles"],
    queryFn: () => apiFetch<InvestorProfile[]>("/profiles"),
  });
}

export function useProfile(profileId: string | undefined) {
  return useQuery({
    queryKey: ["profiles", profileId],
    queryFn: () => apiFetch<InvestorProfile>(`/profiles/${profileId}`),
    enabled: profileId !== undefined,
  });
}

export function useCreateProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: InvestorProfileIn) =>
      apiFetch<InvestorProfile>("/profiles", { method: "POST", body: JSON.stringify(data) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["profiles"] }),
  });
}

export function useUpdateProfile(profileId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: InvestorProfileIn) =>
      apiFetch<InvestorProfile>(`/profiles/${profileId}`, {
        method: "PUT",
        body: JSON.stringify(data),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["profiles"] }),
  });
}

export function useDeleteProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (profileId: string) =>
      apiFetch<void>(`/profiles/${profileId}`, { method: "DELETE" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["profiles"] }),
  });
}

/** Starts the search pipeline for a profile. Returns 501 until CHECKLIST I-09 is built. */
export function useStartRun() {
  return useMutation({
    mutationFn: (profileId: string) =>
      apiFetch<PipelineRun>(`/profiles/${profileId}/runs`, { method: "POST" }),
  });
}

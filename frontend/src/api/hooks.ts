/**
 * TanStack Query hooks, one per endpoint. Add each hook alongside the feature that needs it
 * (CHECKLIST I-10).
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "./client";
import type {
  Alert,
  AlertCheckResult,
  CompareResult,
  SavedProperty,
  SaveRequest,
  AreaDevelopment,
  AreaIntel,
  BudgetStatus,
  CompetitorReport,
  HealthStatus,
  InvestorProfile,
  InvestorProfileIn,
  Listing,
  PipelineRun,
  ProfileOptions,
  PropertyDetail,
  Recommendation,
  TargetSuggestion,
  TargetSuggestionIn,
  Verification,
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

/** Starts the search and verification pipeline for a profile. */
export function useStartRun() {
  return useMutation({
    mutationFn: (profileId: string) =>
      apiFetch<PipelineRun>(`/profiles/${profileId}/runs`, { method: "POST" }),
  });
}

// --- Pipeline runs (I-09, F-02, F-20) --------------------------------------------------

const isActive = (run: PipelineRun | undefined) =>
  run?.status === "pending" || run?.status === "running";

/** A run, polled every second while it is pending or running. */
export function useRun(runId: string | undefined) {
  return useQuery({
    queryKey: ["runs", runId],
    queryFn: () => apiFetch<PipelineRun>(`/runs/${runId}`),
    enabled: runId !== undefined,
    refetchInterval: (query) => (isActive(query.state.data) ? 1000 : false),
  });
}

/** Candidates and partial checks, refreshed as verification advances. */
export function useRunListings(run: PipelineRun | undefined) {
  return useQuery({
    queryKey: ["runs", run?.id, "listings", run?.status, checkedCount(run)],
    queryFn: () => apiFetch<Listing[]>(`/runs/${run?.id}/listings`),
    enabled: hasCandidates(run),
  });
}

function checkedCount(run: PipelineRun | undefined) {
  return run?.events?.find((event) => event.stage === "verify")?.counts?.checked ?? 0;
}

function hasCandidates(run: PipelineRun | undefined) {
  return run !== undefined && (
    !isActive(run) || (run.events ?? []).some((event) => event.stage === "clean" && event.status === "succeeded")
  );
}

export function useRunVerifications(run: PipelineRun | undefined) {
  return useQuery({
    queryKey: ["runs", run?.id, "verifications", run?.status, checkedCount(run)],
    queryFn: () => apiFetch<Verification[]>(`/runs/${run?.id}/verifications`),
    enabled: hasCandidates(run),
  });
}

/** The ranked shortlist (F-04), once the rank stage has finished. */
export function useRunRecommendations(run: PipelineRun | undefined) {
  const ranked = (run?.events ?? []).some(
    (event) => event.stage === "rank" && (event.status === "succeeded" || event.status === "failed"),
  );
  return useQuery({
    queryKey: ["runs", run?.id, "recommendations", run?.status],
    queryFn: () => apiFetch<Recommendation[]>(`/runs/${run?.id}/recommendations`),
    enabled: run !== undefined && ranked,
  });
}

/** Area intelligence for the run's ranked localities (F-05), once enrichment has finished. */
export function useRunAreas(run: PipelineRun | undefined) {
  const enriched = (run?.events ?? []).some(
    (event) => event.stage === "enrich" && (event.status === "succeeded" || event.status === "failed"),
  );
  return useQuery({
    queryKey: ["runs", run?.id, "areas", run?.status],
    queryFn: () => apiFetch<AreaIntel[]>(`/runs/${run?.id}/areas`),
    enabled: run !== undefined && enriched,
  });
}

/** Same-category businesses around each commercial locality (F-06), once enrichment has
 * finished. Empty for residential runs. */
export function useRunCompetitors(run: PipelineRun | undefined) {
  const enriched = (run?.events ?? []).some(
    (event) => event.stage === "enrich" && (event.status === "succeeded" || event.status === "failed"),
  );
  return useQuery({
    queryKey: ["runs", run?.id, "competitors", run?.status],
    queryFn: () => apiFetch<CompetitorReport[]>(`/runs/${run?.id}/competitors`),
    enabled: run !== undefined && enriched,
  });
}

/** Developing-area signals per locality (ADR 0025), once enrichment has finished. Display only. */
export function useRunDevelopment(run: PipelineRun | undefined) {
  const enriched = (run?.events ?? []).some(
    (event) => event.stage === "enrich" && (event.status === "succeeded" || event.status === "failed"),
  );
  return useQuery({
    queryKey: ["runs", run?.id, "development", run?.status],
    queryFn: () => apiFetch<AreaDevelopment[]>(`/runs/${run?.id}/development`),
    enabled: run !== undefined && enriched,
  });
}

// --- Property detail (F-07) ----------------------------------------------------------

/** One property as a run judged it; without a run, the latest run that found it (ADR 0021).
 * Stored results only, so it never spends a search. */
export function usePropertyDetail(listingId: string | undefined, runId: string | undefined) {
  return useQuery({
    queryKey: ["properties", listingId, runId ?? "latest"],
    queryFn: () =>
      apiFetch<PropertyDetail>(
        `/properties/${listingId}${runId ? `?run_id=${encodeURIComponent(runId)}` : ""}`,
      ),
    enabled: listingId !== undefined,
  });
}

/** A sourced, typical target ROI for the profile being written (ADR 0018). Repeat lookups are
 * cached server-side, so refetching when risk appetite changes is cheap. */
export function useTargetSuggestion(input: TargetSuggestionIn | null) {
  return useQuery({
    queryKey: ["target-suggestion", input],
    queryFn: () =>
      apiFetch<TargetSuggestion>("/profiles/target-suggestion", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    enabled: input !== null,
    staleTime: Infinity,
  });
}

// --- Saved properties and comparison (F-08) ------------------------------------------
export function useSaved() {
  return useQuery({ queryKey: ["saved"], queryFn: () => apiFetch<SavedProperty[]>("/saved") });
}

export function useSave() {
  const cache = useQueryClient();
  return useMutation({
    mutationFn: (request: SaveRequest) => apiFetch<SavedProperty>("/saved", {
      method: "POST", body: JSON.stringify(request),
    }),
    onSuccess: () => cache.invalidateQueries({ queryKey: ["saved"] }),
  });
}

export function useUnsave() {
  const cache = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiFetch<void>(`/saved/${id}`, { method: "DELETE" }),
    onSuccess: () => cache.invalidateQueries({ queryKey: ["saved"] }),
  });
}

export function useCompare(ids: string[]) {
  const valid = ids.length >= 2 && ids.length <= 4 && new Set(ids).size === ids.length;
  return useQuery({
    queryKey: ["compare", ids], enabled: valid,
    queryFn: () => apiFetch<CompareResult>(`/compare?${new URLSearchParams(ids.map(id => ["ids", id]))}`),
  });
}

// --- Alerts (F-10) -------------------------------------------------------------------
export function useAlerts(unreadOnly = false) {
  return useQuery({
    queryKey: ["alerts", unreadOnly],
    queryFn: () => apiFetch<Alert[]>(`/alerts?unread_only=${unreadOnly}`),
    refetchInterval: 30_000,
  });
}

export function useCheckAlerts() {
  const cache = useQueryClient();
  return useMutation({
    mutationFn: () => apiFetch<AlertCheckResult>("/alerts/check", { method: "POST" }),
    onSuccess: () => {
      cache.invalidateQueries({ queryKey: ["alerts"] });
      cache.invalidateQueries({ queryKey: ["budget"] });
    },
  });
}

export function useReadAlert() {
  const cache = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiFetch<Alert>(`/alerts/${id}/read`, { method: "POST" }),
    onSuccess: () => cache.invalidateQueries({ queryKey: ["alerts"] }),
  });
}

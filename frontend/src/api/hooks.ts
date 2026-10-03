/**
 * TanStack Query hooks, one per endpoint. Add each hook alongside the feature that needs it
 * (CHECKLIST I-10).
 */

import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "./client";
import type { HealthStatus } from "./types";

export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: () => apiFetch<HealthStatus>("/health"),
    staleTime: 60_000,
  });
}

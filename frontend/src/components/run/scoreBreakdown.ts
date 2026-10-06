import type { Recommendation } from "../../api/types";

const LABELS: Record<string, string> = {
  relevance: "Relevance",
  value: "Value vs area",
  evidence: "Evidence",
  roi: "ROI",
  area: "Area signals",
  flag_penalty: "Flag penalty",
};

const MISSING: Record<string, string> = {
  value: "no price to compare",
  roi: "not available yet",
  area: "not available yet",
};

export interface BreakdownRow {
  key: string;
  label: string;
  points: number | null;
  note?: string;
}

/** Score parts in a fixed order (ADR 0015). A zero penalty is hidden; missing parts say why. */
export function breakdownRows(breakdown: Recommendation["score_breakdown"]): BreakdownRow[] {
  return Object.keys(LABELS).flatMap((key): BreakdownRow[] => {
    const points = breakdown?.[key] ?? null;
    if (key === "flag_penalty" && !points) return [];
    if (points === null && !(key in MISSING)) return [];
    return [{ key, label: LABELS[key], points, note: points === null ? MISSING[key] : undefined }];
  });
}

import type { PipelineRun, RunStatus } from "../../api/types";

const STAGE_LABELS: Record<string, string> = {
  plan: "Plan searches",
  fetch: "Search portals and Maps",
  clean: "Read prices from results",
  verify: "AI check against your profile",
  enrich: "Area and competitor data",
  rank: "Rank and explain",
};

// Singular and plural for the count keys the backend reports (pipeline/orchestrator.py).
const COUNT_WORDS: Record<string, [string, string]> = {
  queries: ["query", "queries"],
  searches: ["search", "searches"],
  live: ["live", "live"],
  retries: ["retry", "retries"],
  pages: ["page", "pages"],
  places: ["place", "places"],
  candidates: ["candidate", "candidates"],
  entries: ["entry", "entries"],
  projects: ["project", "projects"],
  matched: ["matched", "matched"],
  merged: ["merged", "merged"],
};

const countLabel = (key: string, value: number) => {
  const [one, many] = COUNT_WORDS[key] ?? [key, key];
  return `${value} ${value === 1 ? one : many}`;
};

const ICON: Record<RunStatus, { symbol: string; className: string; label: string }> = {
  pending: { symbol: "○", className: "text-slate-400", label: "waiting" },
  running: { symbol: "◐", className: "animate-pulse text-slate-900", label: "running" },
  succeeded: { symbol: "✓", className: "text-emerald-600", label: "done" },
  failed: { symbol: "✕", className: "text-red-600", label: "failed" },
};

/** Live progress of a pipeline run (CHECKLIST F-20). */
export function StageList({ run }: { run: PipelineRun }) {
  return (
    <ol className="divide-y divide-slate-100 rounded-xl border border-slate-200 bg-white">
      {(run.events ?? []).map((event) => {
        const icon = ICON[event.status];
        const counts = Object.entries(event.counts ?? {});
        return (
          <li key={event.stage} className="flex gap-3 px-4 py-3">
            <span aria-label={icon.label} className={`w-4 text-center font-semibold ${icon.className}`}>
              {icon.symbol}
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium">{STAGE_LABELS[event.stage] ?? event.stage}</p>
              {event.message && <p className="text-xs text-slate-500">{event.message}</p>}
            </div>
            {counts.length > 0 && (
              <p className="shrink-0 text-right text-xs text-slate-500">
                {counts.map(([key, value]) => countLabel(key, value)).join(" · ")}
              </p>
            )}
          </li>
        );
      })}
    </ol>
  );
}

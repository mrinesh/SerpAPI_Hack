import { Link, useParams } from "react-router";

import { describeError } from "../api/client";
import { useProfile, useProfileOptions, useRun, useRunListings } from "../api/hooks";
import { Notice } from "../components/Notice";
import { CandidateList } from "../components/run/CandidateList";
import { StageList } from "../components/run/StageList";

/** One discovery run: live progress (F-20), then the candidates it found (F-02). */
export function RunPage() {
  const { runId } = useParams();
  const run = useRun(runId);
  const profile = useProfile(run.data?.profile_id);
  const options = useProfileOptions();
  const listings = useRunListings(run.data);

  if (run.error) return <Notice tone="error">{describeError(run.error)}</Notice>;
  if (!run.data) return <p className="text-sm text-slate-500">Loading…</p>;

  const active = run.data.status === "pending" || run.data.status === "running";
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <Link to="/" className="text-sm text-slate-500 hover:underline">
            ← Profiles
          </Link>
          <h1 className="text-2xl font-semibold tracking-tight">
            {profile.data ? profile.data.name : "Property search"}
          </h1>
          <p className="text-sm text-slate-600">
            {active ? "Searching…" : run.data.status === "failed" ? "Search failed" : "Search finished"}
            {" · "}
            {run.data.searches_used} searches spent · {run.data.cache_hits} served from cache
          </p>
        </div>
      </div>

      {run.data.status === "failed" && run.data.error && (
        <Notice tone="error">{run.data.error}</Notice>
      )}

      <StageList run={run.data} />

      {listings.error && <Notice tone="error">{describeError(listings.error)}</Notice>}
      {listings.data && options.data && (
        <CandidateList listings={listings.data} options={options.data} />
      )}
    </div>
  );
}

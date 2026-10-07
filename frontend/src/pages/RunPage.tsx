import { Link, useParams } from "react-router";

import { describeError } from "../api/client";
import { useProfile, useProfileOptions, useRun, useRunListings, useRunVerifications, useRunAreas, useRunMetrics, useRunDevelopment } from "../api/hooks";
import { Notice } from "../components/Notice";
import { CandidateList } from "../components/run/CandidateList";
import { StageList } from "../components/run/StageList";
import { AreaIntelPanel } from "../components/run/AreaIntelPanel";
import { DevelopmentPanel } from "../components/run/DevelopmentPanel";

/** Discovery and relevance verification, with live progress and partial results. */
export function RunPage() {
  const { runId } = useParams();
  const run = useRun(runId);
  const profile = useProfile(run.data?.profile_id);
  const options = useProfileOptions();
  const listings = useRunListings(run.data);
  const verifications = useRunVerifications(run.data);
  const areas = useRunAreas(run.data);
  const metrics = useRunMetrics(run.data);
  const development = useRunDevelopment(run.data);

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
      {development.error && <Notice tone="error">{describeError(development.error)}</Notice>}
      {development.data && <DevelopmentPanel reports={development.data} />}
      {areas.error && <Notice tone="error">{describeError(areas.error)}</Notice>}
      {areas.data && areas.data.length > 0 && <AreaIntelPanel areas={areas.data} />}

      {listings.error && <Notice tone="error">{describeError(listings.error)}</Notice>}
      {verifications.error && <Notice tone="error">{describeError(verifications.error)}</Notice>}
      {metrics.error && <Notice tone="error">{describeError(metrics.error)}</Notice>}
      {listings.data && options.data && (
        <CandidateList listings={listings.data} options={options.data} verifications={verifications.data ?? []} metrics={metrics.data ?? []} />
      )}
    </div>
  );
}

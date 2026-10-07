import { Link, useParams } from "react-router";

import { describeError } from "../api/client";
import {
  useProfile,
  useProfileOptions,
  useRun,
  useRunListings,
  useRunAreas,
  useRunRecommendations,
  useRunVerifications,
} from "../api/hooks";
import { layoutMap } from "../components/map/mapLayout";
import { MapLegend, ResultsMap } from "../components/map/ResultsMap";
import { Notice } from "../components/Notice";
import { AreaPanel } from "../components/run/AreaPanel";
import { CandidateList } from "../components/run/CandidateList";
import { StageList } from "../components/run/StageList";

/** Discovery and relevance verification, with live progress and partial results. */
export function RunPage() {
  const { runId } = useParams();
  const run = useRun(runId);
  const profile = useProfile(run.data?.profile_id);
  const options = useProfileOptions();
  const listings = useRunListings(run.data);
  const verifications = useRunVerifications(run.data);
  const recommendations = useRunRecommendations(run.data);
  const areas = useRunAreas(run.data);

  if (run.error) return <Notice tone="error">{describeError(run.error)}</Notice>;
  if (!run.data) return <p className="text-sm text-slate-500">Loading…</p>;

  const active = run.data.status === "pending" || run.data.status === "running";
  const layout = listings.data && listings.data.length > 0
    ? layoutMap({
      listings: listings.data,
      verifications: verifications.data ?? [],
      recommendations: recommendations.data ?? [],
      areas: areas.data ?? [],
    })
    : null;
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
      {verifications.error && <Notice tone="error">{describeError(verifications.error)}</Notice>}
      {recommendations.error && <Notice tone="error">{describeError(recommendations.error)}</Notice>}
      {areas.error && <Notice tone="error">{describeError(areas.error)}</Notice>}
      {layout && layout.bounds.length > 0 && (
        <section className="space-y-2">
          <ResultsMap layout={layout} runId={run.data.id} showAmenities={layout.listings.length === 0} />
          <MapLegend layout={layout} />
        </section>
      )}
      {areas.data && options.data && (
        <AreaPanel
          areas={areas.data}
          typeLabel={(value) =>
            options.data.segments.flatMap((s) => s.property_types).find((t) => t.value === value)?.label ?? value}
        />
      )}
      {listings.data && options.data && (
        <CandidateList
          runId={run.data.id}
          listings={listings.data}
          options={options.data}
          verifications={verifications.data ?? []}
          recommendations={recommendations.data ?? []}
          targetRoi={profile.data?.target_roi_pct}
        />
      )}
    </div>
  );
}

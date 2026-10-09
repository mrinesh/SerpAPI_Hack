import { SaveButton } from "../SaveButton";
import { Link } from "react-router";

import type { Recommendation } from "../../api/types";
import { formatInr } from "../../lib/money";
import { accessLine } from "./areaText";
import { FlagChips } from "./FlagChips";
import { metricsLine, targetBadge } from "./metricsText";
import { breakdownRows } from "./scoreBreakdown";

/** F-04: the ranked shortlist. Scores are computed in code; reasons are AI-written for the top
 * picks and code-written for the rest (ADR 0015). */
export function RecommendationList({ runId, recommendations, describe, targetRoi }: {
  runId: string;
  recommendations: Recommendation[];
  describe: (recommendation: Recommendation) => string;
  targetRoi?: number;
}) {
  if (recommendations.length === 0) {
    return <p className="text-sm text-slate-500">No candidates could be ranked.</p>;
  }
  return (
    <ol className="divide-y divide-slate-100 rounded-xl border border-slate-200 bg-white">
      {recommendations.map((recommendation) => (
        <RecommendationCard
          key={recommendation.listing.id}
          runId={runId}
          recommendation={recommendation}
          details={describe(recommendation)}
          targetRoi={targetRoi}
        />
      ))}
    </ol>
  );
}

function RecommendationCard({ runId, recommendation, details, targetRoi }: {
  runId: string;
  recommendation: Recommendation;
  details: string;
  targetRoi?: number;
}) {
  const { listing, verification } = recommendation;
  const returns = metricsLine(recommendation.metrics);
  const badge = targetBadge(recommendation.metrics, targetRoi);
  return (
    <li className="grid gap-3 px-4 py-4 sm:grid-cols-[auto_1fr_auto]">
      <p className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-900 text-sm font-semibold text-white">
        {recommendation.rank}
      </p>
      <div className="min-w-0 space-y-2">
        <div>
          <Link
            to={`/runs/${runId}/properties/${listing.id}`}
            className="block truncate font-medium hover:underline"
            title={listing.name}
          >
            {listing.name}
          </Link>
          <p className="text-xs text-slate-500">{details}</p>
          {accessLine(recommendation.access) && (
            <p className="text-xs text-slate-500">{accessLine(recommendation.access)}</p>
          )}
          {recommendation.metrics?.assessment_note && !badge && (
            <p className="text-xs text-slate-500">{recommendation.metrics.assessment_note}</p>
          )}
          {(returns || badge) && (
            <p className="text-xs text-slate-600">
              {returns}
              {badge && (
                <span
                  className={`ml-2 rounded-full border px-2 py-0.5 font-medium ${
                    recommendation.metrics?.meets_target_roi
                      ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                      : "border-slate-200 bg-slate-50 text-slate-600"
                  }`}
                  title="Estimated from area rents and quoted prices, before costs"
                >
                  {badge}
                </span>
              )}
            </p>
          )}
        </div>
        <p className="text-sm text-slate-700">
          {recommendation.reason}
          {recommendation.explained && (
            <span className="ml-1 text-xs text-slate-400" title="Written by AI from the figures shown; every number is checked">
              · AI summary
            </span>
          )}
        </p>
        <FlagChips flags={verification.flags ?? []} />
        <div className="grid gap-2 text-xs sm:grid-cols-2">
          <Points label="Highlights" items={recommendation.highlights ?? []} />
          <Points label="Risks" items={recommendation.risks ?? []} />
        </div>
        <Breakdown recommendation={recommendation} />
      </div>
      <div className="text-left sm:text-right">
          <SaveButton listingId={listing.id} />
        <p className="text-lg font-semibold">
          {recommendation.score}
          <span className="text-xs font-normal text-slate-500">/100</span>
        </p>
        {listing.price_inr.value != null && (
          <p className="text-sm">{formatInr(listing.price_inr.value)}</p>
        )}
        {listing.url && (
          <a href={listing.url} target="_blank" rel="noreferrer" className="text-xs text-slate-600 underline hover:text-slate-900">
            Source ↗
          </a>
        )}
      </div>
    </li>
  );
}

export function Points({ label, items }: { label: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div>
      <p className="font-medium text-slate-600">{label}</p>
      <ul className="list-disc space-y-0.5 pl-4 text-slate-500">
        {items.map((item, index) => <li key={`${index}-${item}`}>{item}</li>)}
      </ul>
    </div>
  );
}

export function Breakdown({ recommendation }: { recommendation: Recommendation }) {
  return (
    <p className="text-xs text-slate-500">
      <span className="font-medium text-slate-600">Score: </span>
      {breakdownRows(recommendation.score_breakdown)
        .map((row) => `${row.label} ${row.points ?? `– ${row.note}`}`)
        .join(" · ")}
    </p>
  );
}

import type { Recommendation } from "../../api/types";
import { formatInr } from "../../lib/money";
import { FlagChips } from "./FlagChips";
import { breakdownRows } from "./scoreBreakdown";

/** F-04: the ranked shortlist. Scores are computed in code; reasons are AI-written for the top
 * picks and code-written for the rest (ADR 0015). */
export function RecommendationList({ recommendations, describe }: {
  recommendations: Recommendation[];
  describe: (recommendation: Recommendation) => string;
}) {
  if (recommendations.length === 0) {
    return <p className="text-sm text-slate-500">No candidates could be ranked.</p>;
  }
  return (
    <ol className="divide-y divide-slate-100 rounded-xl border border-slate-200 bg-white">
      {recommendations.map((recommendation) => (
        <RecommendationCard
          key={recommendation.listing.id}
          recommendation={recommendation}
          details={describe(recommendation)}
        />
      ))}
    </ol>
  );
}

function RecommendationCard({ recommendation, details }: {
  recommendation: Recommendation;
  details: string;
}) {
  const { listing, verification } = recommendation;
  return (
    <li className="grid gap-3 px-4 py-4 sm:grid-cols-[auto_1fr_auto]">
      <p className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-900 text-sm font-semibold text-white">
        {recommendation.rank}
      </p>
      <div className="min-w-0 space-y-2">
        <div>
          <p className="truncate font-medium" title={listing.name}>{listing.name}</p>
          <p className="text-xs text-slate-500">{details}</p>
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

function Points({ label, items }: { label: string; items: string[] }) {
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

function Breakdown({ recommendation }: { recommendation: Recommendation }) {
  return (
    <p className="text-xs text-slate-500">
      <span className="font-medium text-slate-600">Score: </span>
      {breakdownRows(recommendation.score_breakdown)
        .map((row) => `${row.label} ${row.points ?? `– ${row.note}`}`)
        .join(" · ")}
    </p>
  );
}

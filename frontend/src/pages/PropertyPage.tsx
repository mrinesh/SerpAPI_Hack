import { SaveButton } from "../components/SaveButton";
import { RiskCard } from "../components/run/RiskCard";
import type { ReactNode } from "react";
import { Link, useParams } from "react-router";

import { describeError } from "../api/client";
import { useProfile, useProfileOptions, usePropertyDetail } from "../api/hooks";
import type { PropertyDetail, PropertyType } from "../api/types";
import { layoutMap } from "../components/map/mapLayout";
import { MapLegend, ResultsMap } from "../components/map/ResultsMap";
import { Notice } from "../components/Notice";
import { AreaCard } from "../components/run/AreaPanel";
import { CompetitorCard } from "../components/run/CompetitorCard";
import { accessLine } from "../components/run/areaText";
import { PORTAL_LABELS, STATUS_LABELS, VerificationSummary } from "../components/run/CandidateList";
import { targetBadge } from "../components/run/metricsText";
import { Breakdown, Points } from "../components/run/RecommendationList";
import { groupSources, sourceLabel } from "../components/sourced";
import { SourcedValue } from "../components/SourcedValue";
import { formatInr } from "../lib/money";

const signedPct = (value: number) => `${value > 0 ? "+" : ""}${value.toFixed(1)}%`;
const sqft = (value: number) => `${Math.round(value).toLocaleString("en-IN")} sq ft`;
const perSqft = (value: number) => `₹${Math.round(value).toLocaleString("en-IN")}/sq ft`;

/** F-07: one property as one search judged it, with every figure's source (F-11), on a map with
 * its area's amenities (F-19) and, for commercial properties, same-category businesses nearby
 * (F-06). Built from stored results only (ADR 0021). */
export function PropertyPage() {
  const { runId, listingId } = useParams();
  const detail = usePropertyDetail(listingId, runId);
  const options = useProfileOptions();
  const profile = useProfile(detail.data?.profile_id);

  if (detail.error) return <Notice tone="error">{describeError(detail.error)}</Notice>;
  if (options.error) return <Notice tone="error">{describeError(options.error)}</Notice>;
  if (!detail.data || !options.data) return <p className="text-sm text-slate-500">Loading…</p>;

  const data = detail.data;
  const { listing, verification, recommendation, metrics } = data;
  const typeLabel = (value: string | null | undefined) =>
    options.data.segments.flatMap((s) => s.property_types).find((t) => t.value === value)?.label ?? value ?? "";
  const localityName = (slug: string | null | undefined) =>
    options.data.localities.find((l) => l.slug === slug)?.name ?? slug ?? "";
  const badge = targetBadge(metrics, profile.data?.target_roi_pct);

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0 space-y-1">
          <Link to={`/runs/${data.run_id}`} className="text-sm text-slate-500 hover:underline">
            ← {profile.data ? `${profile.data.name} results` : "Search results"}
          </Link>
          <h1 className="text-2xl font-semibold tracking-tight">{listing.name}</h1>
          <p className="text-sm text-slate-600">
            {[
              typeLabel(listing.property_type.value),
              localityName(listing.locality.value),
              listing.status.value && STATUS_LABELS[listing.status.value],
              `Found on ${PORTAL_LABELS[listing.portal]}`,
            ].filter(Boolean).join(" · ")}
          </p>
          {!runId && (
            <p className="text-xs text-slate-500">Shown as the latest search that found it judged it.</p>
          )}
        </div>
        <div className="text-left sm:text-right">
          <SaveButton listingId={listing.id} />
          <Link className="ml-3 text-sm underline" to={`/portfolio?listing_id=${encodeURIComponent(listing.id)}`}>Track purchase</Link>
          <a className="ml-3 text-sm underline" href={`/api/properties/${encodeURIComponent(listing.id)}/report.pdf?run_id=${encodeURIComponent(data.run_id)}`}>Download PDF report</a>
          {listing.price_inr.value != null && (
            <p className="text-2xl font-semibold">{formatInr(listing.price_inr.value)}</p>
          )}
          {recommendation ? (
            <p className="text-sm text-slate-600">
              Rank {recommendation.rank} · Score <span className="font-semibold">{recommendation.score}</span>/100
            </p>
          ) : (
            <p className="text-sm text-slate-500">Not ranked</p>
          )}
        </div>
      </header>

      <Card title="Facts" note="Each figure shows how sure we are and where it came from.">
        <dl className="grid gap-4 sm:grid-cols-3">
          <SourcedValue label="Price" fact={listing.price_inr} format={formatInr} />
          <SourcedValue label="Size" fact={listing.size_sqft} format={sqft} />
          <SourcedValue label="Price per sq ft" fact={listing.price_per_sqft} format={perSqft} />
          <SourcedValue label="Bedrooms" fact={listing.bedrooms} format={(value) => `${value} BHK`} />
          <SourcedValue label="Status" fact={listing.status} format={(value) => STATUS_LABELS[value]} />
          <SourcedValue label="Type" fact={listing.property_type} format={(value) => typeLabel(value)} />
          <SourcedValue label="Locality" fact={listing.locality} format={(value) => localityName(value)} />
          <SourcedValue
            label="Location"
            fact={listing.location}
            format={(point) => (
              <a
                href={`https://www.google.com/maps?q=${point.lat},${point.lng}`}
                target="_blank"
                rel="noreferrer"
                className="underline"
              >
                {point.lat.toFixed(4)}, {point.lng.toFixed(4)}
              </a>
            )}
          />
          {listing.rating != null && (
            <div className="space-y-0.5">
              <dt className="text-xs text-slate-500">Google Maps rating</dt>
              <dd className="font-medium">{listing.rating}★ ({listing.reviews ?? 0} reviews)</dd>
            </div>
          )}
        </dl>
        {listing.evidence && (
          <blockquote className="mt-4 border-l-2 border-slate-200 pl-3 text-xs text-slate-500">
            “{listing.evidence}”
            {listing.url && (
              <>
                {" "}
                <a href={listing.url} target="_blank" rel="noreferrer" className="underline">
                  {PORTAL_LABELS[listing.portal]} page ↗
                </a>
              </>
            )}
            <p className="mt-1 text-slate-400">The portal search page that quoted it, not a single unit.</p>
          </blockquote>
        )}
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Relevance check">
          {verification
            ? <VerificationSummary verification={verification} />
            : <p className="text-sm text-slate-500">Not AI-checked in this search: each search checks a limited number of candidates.</p>}
        </Card>

        <Card title="Investment metrics" note={metrics ? "Estimated from area rents and quoted prices, before costs." : undefined}>
          {metrics ? (
            <>
              <dl className="grid gap-4 sm:grid-cols-2">
                <SourcedValue label="Price vs area level" fact={metrics.price_vs_area_pct} format={signedPct} />
                <SourcedValue label="Area level" fact={metrics.area_avg_price_per_sqft} format={perSqft} />
                <SourcedValue label="Estimated rent" fact={metrics.est_monthly_rent_inr} format={(value) => `${formatInr(value)}/month`} />
                <SourcedValue label="Rental yield" fact={metrics.rental_yield_pct} format={(value) => `${value.toFixed(1)}%`} />
                <SourcedValue label="Price growth" fact={metrics.price_growth_pct} format={signedPct} />
                <SourcedValue label="Total return" fact={metrics.total_return_pct} format={(value) => `${value.toFixed(1)}%`} />
              </dl>
              {badge && (
                <p className={`mt-3 inline-block rounded-full border px-2 py-0.5 text-xs font-medium ${
                  metrics.meets_target_roi
                    ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                    : "border-slate-200 bg-slate-50 text-slate-600"
                }`}>
                  {badge}
                </p>
              )}
              {metrics.assessment_note && !badge && (
                <p className="mt-3 text-xs text-slate-500">{metrics.assessment_note}</p>
              )}
            </>
          ) : (
            <p className="text-sm text-slate-500">Metrics are computed for ranked candidates only.</p>
          )}
        </Card>
      </div>

      {recommendation && (
        <Card title="Why it ranks here">
          <div className="space-y-3 text-sm">
            <p className="text-slate-700">
              {recommendation.reason}
              {recommendation.explained && (
                <span className="ml-1 text-xs text-slate-400" title="Written by AI from the figures shown; every number is checked">
                  · AI summary
                </span>
              )}
            </p>
            {accessLine(recommendation.access) && (
              <p className="text-xs text-slate-500">{accessLine(recommendation.access)}</p>
            )}
            <div className="grid gap-2 text-xs sm:grid-cols-2">
              <Points label="Highlights" items={recommendation.highlights ?? []} />
              <Points label="Risks" items={recommendation.risks ?? []} />
            </div>
            <Breakdown recommendation={recommendation} />
          </div>
        </Card>
      )}

      <PropertyMap detail={data} />
      {data.risk && <RiskCard report={data.risk} />}

      {data.area && <AreaCard area={data.area} typeLabel={(value: PropertyType) => typeLabel(value)} />}

      {data.competitors && (
        <CompetitorCard
          report={data.competitors}
          typeLabel={(value: PropertyType) => typeLabel(value)}
          only={listing.property_type.value}
        />
      )}

      <PriceHistory history={data.price_history ?? []} />

      <Sources sources={data.sources ?? []} />
    </div>
  );
}

function Card({ title, note, children }: { title: string; note?: string; children: ReactNode }) {
  return (
    <section className="space-y-3 rounded-xl border border-slate-200 bg-white p-4">
      <header>
        <h2 className="font-semibold">{title}</h2>
        {note && <p className="text-xs text-slate-500">{note}</p>}
      </header>
      {children}
    </section>
  );
}

/** The property at its own GPS, or at its locality centre when none was quoted, with the area's
 * metro stations, schools and hospitals. */
function PropertyMap({ detail }: { detail: PropertyDetail }) {
  const layout = layoutMap({
    listings: [detail.listing],
    verifications: detail.verification ? [detail.verification] : [],
    recommendations: detail.recommendation ? [detail.recommendation] : [],
    areas: detail.area ? [detail.area] : [],
    competitors: detail.competitors ? [detail.competitors] : [],
    fitAmenities: true,
  });
  if (layout.bounds.length === 0) return null;
  const exact = layout.listings.length > 0;
  return (
    <Card
      title="On the map"
      note={exact
        ? `Position from Google Maps, with the nearest metro stations, schools and hospitals${detail.competitors ? ` and ${detail.competitors.business_type} nearby` : ""}.`
        : layout.localities.length > 0
        ? `No position was quoted for this property; the dashed marker is the ${layout.localities[0].locality} centre.`
        : "No position was quoted for this property; the area's amenities are shown."}
    >
      <ResultsMap layout={layout} runId={detail.run_id} focusId={detail.listing.id} showAmenities showFiltered className="h-80" />
      <MapLegend layout={layout} />
    </Card>
  );
}

/** Quoted prices across searches; shown once there is more than one. */
function PriceHistory({ history }: { history: PropertyDetail["price_history"] & object }) {
  if (history.length < 2) return null;
  return (
    <Card title="Price seen across searches">
      <ul className="space-y-1 text-sm">
        {history.map((point) => (
          <li key={`${point.run_id}-${point.seen_at}`} className="flex justify-between gap-4">
            <Link to={`/runs/${point.run_id}`} className="text-slate-600 hover:underline">
              {new Date(point.seen_at).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}
            </Link>
            <span className="font-medium">{point.price_inr != null ? formatInr(point.price_inr) : "No price"}</span>
          </li>
        ))}
      </ul>
    </Card>
  );
}

/** F-11: every source behind the figures on this page. */
function Sources({ sources }: { sources: PropertyDetail["sources"] & object }) {
  if (sources.length === 0) return null;
  return (
    <Card title="Where this came from" note="Every search result behind the figures on this page, via SerpApi.">
      <div className="grid gap-4 text-xs sm:grid-cols-2">
        {groupSources(sources).map((group) => (
          <div key={group.engine}>
            <p className="font-medium text-slate-600">{group.label} ({group.items.length})</p>
            <ul className="space-y-0.5 text-slate-500">
              {group.items.map((source, index) => (
                <li key={`${index}-${source.url ?? source.search_id}`} className="truncate">
                  {source.url
                    ? <a href={source.url} target="_blank" rel="noreferrer" className="underline" title={source.url}>{sourceLabel(source)}</a>
                    : sourceLabel(source)}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </Card>
  );
}

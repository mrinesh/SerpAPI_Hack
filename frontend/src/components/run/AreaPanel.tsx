import type { ReactNode } from "react";

import type { AreaIntel, PropertyType } from "../../api/types";
import { areaWarnings, commuteRows, nearestByCategory, newsForPanel } from "./areaText";

/** F-05: one card per locality of the ranked candidates. Distances are computed in code; the
 * summary is AI-written only when every number in it was checked (ADR 0016). */
export function AreaPanel({ areas, typeLabel, children }: {
  areas: AreaIntel[];
  typeLabel: (value: PropertyType) => string;
  children?: ReactNode; // more cards in the same grid, e.g. competitors (F-06)
}) {
  if (areas.length === 0) return null;
  return (
    <section className="grid items-start gap-3 md:grid-cols-2">
      {areas.map((area) => <AreaCard key={area.locality_key} area={area} typeLabel={typeLabel} />)}
      {children}
    </section>
  );
}

export function AreaCard({ area, typeLabel }: { area: AreaIntel; typeLabel: (value: PropertyType) => string }) {
  const levels = Object.entries(area.price_levels ?? {}) as [PropertyType, NonNullable<AreaIntel["price_levels"]>[string]][];
  const rents = area.rent_levels ?? {};
  const growth = area.price_growth_pct;
  return (
    <article className="space-y-3 rounded-xl border border-slate-200 bg-white p-4 text-sm">
      <header className="flex items-baseline justify-between gap-2">
        <h2 className="font-semibold">{area.locality}</h2>
        {area.summary_by_ai && (
          <span className="text-xs text-slate-400" title="Written by AI from the figures shown; every number is checked">
            AI summary
          </span>
        )}
      </header>
      {areaWarnings(area).length > 0 && (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-2 text-xs text-amber-800">
          <p className="font-medium">Some area data could not be loaded; it will be retried on the next search.</p>
          <ul className="list-disc pl-4">
            {areaWarnings(area).map((line) => <li key={line}>{line}</li>)}
          </ul>
        </div>
      )}
      {area.summary && <p className="text-slate-700">{area.summary}</p>}
      {area.infrastructure_summary && <p className="text-slate-600">{area.infrastructure_summary}</p>}
      <dl className="grid grid-cols-2 gap-2 text-xs">
        {levels.map(([kind, level]) => (
          <div key={kind}>
            <dt className="text-slate-500">{typeLabel(kind)} price level</dt>
            <dd className="font-medium" title={level.note ?? undefined}>
              ₹{Math.round(level.value ?? 0).toLocaleString("en-IN")}/sq ft
            </dd>
          </div>
        ))}
        {Object.entries(rents).map(([kind, rent]) => rent?.value != null && (
          <div key={`rent-${kind}`}>
            <dt className="text-slate-500">{typeLabel(kind as PropertyType)} rent</dt>
            <dd className="font-medium" title={rent.note ?? undefined}>
              ₹{rent.value}/sq ft/month
            </dd>
          </div>
        ))}
        {growth?.value != null && (
          <div>
            <dt className="text-slate-500">Price change, past 12 months</dt>
            <dd className="font-medium" title={growth.note ?? undefined}>
              {growth.value > 0 ? "+" : ""}{growth.value}%{" "}
              {growth.sources?.[0]?.url && (
                <a href={growth.sources[0].url} target="_blank" rel="noreferrer" className="font-normal text-slate-500 underline">
                  source
                </a>
              )}
            </dd>
          </div>
        )}
      </dl>
      <div className="grid gap-2 text-xs sm:grid-cols-3">
        {nearestByCategory(area).map((group) => (
          <div key={group.label}>
            <p className="font-medium text-slate-600">{group.label}</p>
            <ul className="space-y-0.5 text-slate-500">
              {group.items.map((amenity) => (
                <li key={amenity.name}>
                  {amenity.source.url
                    ? <a href={amenity.source.url} target="_blank" rel="noreferrer" className="underline">{amenity.name}</a>
                    : amenity.name}
                  {amenity.distance_km != null && ` · ${amenity.distance_km.toFixed(1)} km`}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <Commutes area={area} />
      <LocalNews area={area} />
      <p className="text-xs text-slate-400">
        Amenities come from one Google Maps search per category near the locality centre, so counts are a sample.
        Price change is past data, not a forecast.
      </p>
    </article>
  );
}

/** Weekday 9 AM drive from the locality centre to each job hub, as Google Maps quotes it with its
 * usual traffic (F-23). Display only: it does not change the score (ADR 0026). */
function Commutes({ area }: { area: AreaIntel }) {
  const rows = commuteRows(area);
  if (rows.length === 0) return null;
  return (
    <div className="space-y-1 text-xs">
      <p className="font-medium text-slate-600">Drive to job hubs, weekday 9 AM</p>
      <ul className="space-y-0.5 text-slate-600">
        {rows.map((row) => (
          <li key={row.hub} className="flex flex-wrap items-baseline gap-x-1">
            <span>{row.hub}:</span>
            <span className="font-medium text-slate-800">{row.time}</span>
            {row.typical && <span className="text-slate-500">({row.typical})</span>}
            <span className="text-slate-400">
              · {row.route}
              {row.url && <>{" · "}<a href={row.url} target="_blank" rel="noreferrer" className="underline">route</a></>}
            </span>
          </li>
        ))}
      </ul>
      <p className="text-slate-400">From the locality centre, by car, with Google's usual traffic for that hour; not a guarantee.</p>
    </div>
  );
}

const SENTIMENT_STYLES: Record<string, string> = {
  positive: "border-emerald-200 bg-emerald-50 text-emerald-800",
  negative: "border-red-200 bg-red-50 text-red-700",
  neutral: "border-slate-200 bg-slate-50 text-slate-600",
};

/** Recent locality news as published, with AI topic and sentiment labels (display only). */
function LocalNews({ area }: { area: AreaIntel }) {
  const items = newsForPanel(area);
  if (items.length === 0) return null;
  return (
    <div className="space-y-1 text-xs">
      <p className="font-medium text-slate-600">Local news</p>
      <ul className="space-y-1">
        {items.map((item) => (
          <li key={item.url} className="flex flex-wrap items-baseline gap-1 text-slate-600">
            {item.classified && (
              <span className={`rounded-full border px-1.5 ${SENTIMENT_STYLES[item.sentiment ?? "neutral"]}`}>
                {item.topic}
              </span>
            )}
            <a href={item.url} target="_blank" rel="noreferrer" className="underline">{item.title}</a>
            <span className="text-slate-400">
              {[item.outlet, item.published_on].filter(Boolean).join(" · ")}
            </span>
          </li>
        ))}
      </ul>
      <p className="text-slate-400">Headlines as published; a planned project is not a completed one. Labels are AI-assigned.</p>
    </div>
  );
}

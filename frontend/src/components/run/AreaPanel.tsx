import type { AreaIntel, PropertyType } from "../../api/types";
import { nearestByCategory } from "./areaText";

/** F-05: one card per locality of the ranked candidates. Distances are computed in code; the
 * summary is AI-written only when every number in it was checked (ADR 0016). */
export function AreaPanel({ areas, typeLabel }: {
  areas: AreaIntel[];
  typeLabel: (value: PropertyType) => string;
}) {
  if (areas.length === 0) return null;
  return (
    <section className="grid gap-3 md:grid-cols-2">
      {areas.map((area) => <AreaCard key={area.locality_key} area={area} typeLabel={typeLabel} />)}
    </section>
  );
}

function AreaCard({ area, typeLabel }: { area: AreaIntel; typeLabel: (value: PropertyType) => string }) {
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
      <p className="text-xs text-slate-400">
        Amenities come from one Google Maps search per category near the locality centre, so counts are a sample.
        Price change is past data, not a forecast.
      </p>
    </article>
  );
}

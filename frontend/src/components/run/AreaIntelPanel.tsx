import type { AreaIntel } from "../../api/types";

/** F-05's own evidence links; the general property/citation screens remain future features. */
export function AreaIntelPanel({ areas }: { areas: AreaIntel[] }) {
  return (
    <section className="space-y-3" aria-label="Area intelligence">
      <h2 className="text-lg font-semibold">Area intelligence</h2>
      {areas.map((area) => (
        <article key={area.locality_key} className="rounded-xl border border-slate-200 bg-white p-5 space-y-4">
          <div>
            <h3 className="font-semibold">{area.locality}, {area.city}</h3>
            <p className="text-sm text-slate-600">{area.summary}</p>
            <p className="text-xs text-slate-500">
              Assembled {new Date(area.fetched_at).toLocaleString()}
              {area.cache_hit ? " · Reused locality cache" : ""}
              {area.stale ? " · Refresh due; rerun this profile" : ""}
            </p>
          </div>
          {(area.warnings ?? []).length > 0 && (
            <div className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900" role="status">
              <p className="font-medium">Some area data is unavailable</p>
              <ul className="mt-1 space-y-1">
                {area.warnings!.map((issue, i) => <li key={i}>{issue.operation}: {issue.message}</li>)}
              </ul>
            </div>
          )}
          <div>
            <h4 className="text-sm font-medium">Nearby amenities</h4>
            <p className="text-xs text-slate-500">Distances are straight-line from the locality centre, within 10 km.</p>
            {(area.amenities ?? []).length === 0 ? <p className="text-sm text-slate-500">No amenity matches available.</p> : (
              <ul className="mt-2 grid gap-2 sm:grid-cols-2 lg:grid-cols-3 text-sm">
                {area.amenities!.map((item, i) => (
                  <li key={`${item.category}-${i}`}>
                    <a href={item.source.url ?? undefined} target="_blank" rel="noreferrer" className="text-blue-700 hover:underline">{item.name}</a>
                    <p className="text-xs text-slate-500">{item.category} · {item.distance_km == null ? "Distance unavailable" : `${item.distance_km.toFixed(2)} km`}</p>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div>
            <h4 className="text-sm font-medium">Infrastructure evidence</h4>
            {(area.infrastructure ?? []).length === 0 ? <p className="text-sm text-slate-500">No supported infrastructure summary available.</p> : (
              <ul className="mt-2 space-y-2 text-sm">
                {area.infrastructure!.map((fact, i) => (
                  <li key={i}>
                    <blockquote>{fact.evidence.value}</blockquote>
                    <a href={fact.evidence.sources?.[0]?.url ?? undefined} target="_blank" rel="noreferrer" className="text-xs text-blue-700 hover:underline">News evidence · {fact.topic}</a>
                  </li>
                ))}
              </ul>
            )}
            <p className="mt-1 text-xs text-slate-500">News reports do not independently verify project completion.</p>
          </div>
          <details className="text-sm">
            <summary className="cursor-pointer font-medium">Locality news ({area.news?.length ?? 0})</summary>
            <ul className="mt-2 space-y-2">
              {(area.news ?? []).map((item) => (
                <li key={item.url}>
                  <a href={item.url} target="_blank" rel="noreferrer" className="text-blue-700 hover:underline">{item.title}</a>
                  <p className="text-xs text-slate-500">{item.outlet ?? "Publication unavailable"} · {item.published_on ?? item.published_text ?? "Date unavailable"} · {item.topic} · {item.sentiment}</p>
                </li>
              ))}
            </ul>
          </details>
          {Object.keys(area.price_levels ?? {}).length > 0 && (
            <div className="text-sm">
              <h4 className="font-medium">Existing locality price benchmarks</h4>
              {Object.entries(area.price_levels ?? {}).map(([kind, level]) => (
                <p key={kind}>{kind}: {level.value == null ? "Unavailable" : `₹${level.value.toLocaleString("en-IN")}/sq ft`} · <a href={level.sources?.[0]?.url ?? undefined} target="_blank" rel="noreferrer" className="text-blue-700 hover:underline">Source</a></p>
              ))}
            </div>
          )}
        </article>
      ))}
    </section>
  );
}

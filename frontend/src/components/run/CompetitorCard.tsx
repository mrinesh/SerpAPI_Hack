import type { CompetitorReport, PropertyType } from "../../api/types";
import { countLine, readingLines } from "./competitorText";

const NEAREST = 6;

/** F-06: same-category businesses around one commercial locality. Shown, not scored (ADR 0023).
 * With `only`, the readings for that property type alone (the detail page). */
export function CompetitorCard({ report, typeLabel, only }: {
  report: CompetitorReport;
  typeLabel: (value: PropertyType) => string;
  only?: PropertyType | null;
}) {
  const places = report.competitors ?? [];
  const lines = readingLines(report, only);
  return (
    <article className="space-y-3 rounded-xl border border-slate-200 bg-white p-4 text-sm">
      <header>
        <h2 className="font-semibold">{report.business_type} near {report.locality}</h2>
        <p className="text-xs text-slate-500">Same-category businesses from Google Maps. Shown for context; not part of the score.</p>
      </header>
      {report.status === "failed" ? (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-2 text-xs text-amber-800">
          <p className="font-medium">Nearby businesses could not be loaded; they will be retried on the next search.</p>
          {report.warning && <p>{report.warning.message}</p>}
        </div>
      ) : (
        <>
          <p className="text-slate-700">{countLine(report)}</p>
          {places.length > 0 && lines.map((line) => (
            <div key={line.type}>
              <p className="font-medium text-slate-800">
                {line.label}
                {lines.length > 1 && !only && <span className="font-normal text-slate-500"> · for {typeLabel(line.type)}</span>}
              </p>
              <p className="text-slate-600">{line.text}</p>
            </div>
          ))}
          {places.length > 0 && (
            <dl className="grid grid-cols-3 gap-2 text-xs">
              <div>
                <dt className="text-slate-500">Density</dt>
                <dd className="font-medium">{report.density_per_sq_km} per sq km</dd>
              </div>
              <div>
                <dt className="text-slate-500">Average rating</dt>
                <dd className="font-medium">{report.avg_rating != null ? `${report.avg_rating}★` : "—"}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Reviews, all places</dt>
                <dd className="font-medium">{(report.total_reviews ?? 0).toLocaleString("en-IN")}</dd>
              </div>
            </dl>
          )}
          {places.length > 0 && (
            <div className="text-xs">
              <p className="font-medium text-slate-600">Nearest</p>
              <ul className="space-y-0.5 text-slate-500">
                {places.slice(0, NEAREST).map((place) => (
                  <li key={place.place_id ?? place.name}>
                    {place.source.url
                      ? <a href={place.source.url} target="_blank" rel="noreferrer" className="underline">{place.name}</a>
                      : place.name}
                    {" · "}{place.distance_km} km
                    {place.category && ` · ${place.category}`}
                    {place.rating != null && ` · ${place.rating}★ (${place.reviews ?? 0})`}
                  </li>
                ))}
              </ul>
              {places.length > NEAREST && <p className="text-slate-400">+{places.length - NEAREST} more on the map.</p>}
            </div>
          )}
        </>
      )}
    </article>
  );
}

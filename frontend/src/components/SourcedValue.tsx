import type { ReactNode } from "react";

import type { SourcedField } from "../api/types";
import { confidenceLevel, METHOD_LABELS, sourceLabel } from "./sourced";

const BADGE_STYLES = {
  high: "border-emerald-200 bg-emerald-50 text-emerald-800",
  medium: "border-amber-200 bg-amber-50 text-amber-800",
  low: "border-slate-200 bg-slate-50 text-slate-600",
};

/** F-11: a sourced fact with its confidence, how it was found and where. A missing value shows
 * as "—" with the reason, never as 0. */
export function SourcedValue<T extends SourcedField>({ label, fact, format }: {
  label: string;
  fact: T | null | undefined;
  format: (value: NonNullable<T["value"]>) => ReactNode;
}) {
  const value = fact?.value;
  const level = confidenceLevel(fact?.confidence);
  const sources = fact?.sources ?? [];
  return (
    <div className="space-y-0.5">
      <dt className="text-xs text-slate-500">{label}</dt>
      <dd className="flex flex-wrap items-baseline gap-1.5">
        <span className="font-medium">{value != null ? format(value as NonNullable<T["value"]>) : "—"}</span>
        {value != null && fact && (
          <span
            className={`rounded-full border px-1.5 text-[11px] ${BADGE_STYLES[level]}`}
            title={`${Math.round((fact.confidence ?? 0) * 100)}% confidence`}
          >
            {level}
          </span>
        )}
      </dd>
      {fact && (value != null || fact.note) && (
        <details className="text-xs text-slate-500">
          <summary className="cursor-pointer select-none hover:text-slate-700">
            {value != null ? METHOD_LABELS[fact.method] : fact.note}
          </summary>
          <div className="mt-1 space-y-0.5 border-l border-slate-200 pl-2">
            {value != null && fact.note && <p>{fact.note}</p>}
            {sources.map((source, index) => (
              <p key={`${index}-${source.url ?? source.search_id}`}>
                {source.url
                  ? <a href={source.url} target="_blank" rel="noreferrer" className="underline">{sourceLabel(source)}</a>
                  : sourceLabel(source)}
              </p>
            ))}
            {sources.length === 0 && value != null && <p>No external source: {METHOD_LABELS[fact.method].toLowerCase()}.</p>}
          </div>
        </details>
      )}
    </div>
  );
}

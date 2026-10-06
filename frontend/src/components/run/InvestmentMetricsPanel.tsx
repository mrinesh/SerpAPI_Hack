import type { InvestmentMetrics, SourceRef } from "../../api/types";
import { formatInr } from "../../lib/money";

type Fact = { value?: number | null; confidence?: number; note?: string | null; sources?: SourceRef[] };
const MEASURE = { rental_yield: "Gross rental yield", price_growth: "Price growth", total_return: "Illustrative total return" };

export function InvestmentMetricsPanel({ metrics: m }: { metrics: InvestmentMetrics }) {
  return (
    <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs">
      <p className="font-medium text-slate-800">Investment comparison</p>
      <dl className="mt-2 grid gap-2 sm:grid-cols-2">
        <Metric label="Price per sq ft" fact={m.price_per_sqft} money />
        <Metric label="Same-type area benchmark / sq ft" fact={m.area_avg_price_per_sqft} money />
        <Metric label="Price above/below benchmark" fact={m.price_vs_area_pct} />
        <Metric label="Estimated monthly asking rent" fact={m.est_monthly_rent_inr} money />
        <Metric label="Gross rental yield before costs" fact={m.rental_yield_pct} />
        <Metric label={m.price_growth_pct.method === "query" ? "Your growth assumption" : "Reported past annual price growth"} fact={m.price_growth_pct} />
        <Metric label="Illustrative total return before costs" fact={m.total_return_pct} />
      </dl>
      <p className="mt-2 font-medium text-slate-700">
        {MEASURE[m.roi_measure]} target: {m.target_roi_pct}% · {m.meets_target_roi == null
          ? "Unable to assess" : m.meets_target_roi ? "Meets target" : "Below target"}
      </p>
      {m.assessment_note && <p className="mt-1 text-slate-500">{m.assessment_note}</p>}
      <p className="mt-2 text-slate-500">Asking rents are estimates. Yield excludes vacancy, maintenance and taxes. Past growth and your assumptions are not forecasts.</p>
    </div>
  );
}

function Metric({ label, fact, money }: { label: string; fact: Fact; money?: boolean }) {
  return (
    <div>
      <dt className="text-slate-500">{label}</dt>
      <dd className="font-medium text-slate-700">
        {fact.value == null ? "Unavailable" : money ? formatInr(fact.value) : `${fact.value.toFixed(2)}%`}
      </dd>
      <details className="text-slate-500">
        <summary className="cursor-pointer">Evidence · {Math.round((fact.confidence ?? 0) * 100)}% confidence</summary>
        <p>{fact.note}</p>
        {(fact.sources ?? []).map((source, index) => source.url && (
          <a key={`${source.url}-${index}`} href={source.url} target="_blank" rel="noreferrer" className="block underline">{source.title ?? "Source"}</a>
        ))}
      </details>
    </div>
  );
}

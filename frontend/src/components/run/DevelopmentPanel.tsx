import type { AreaDevelopment, SearchMomentum } from "../../api/types";

const SIGNALS = {
  corroborated_growth: "Developing-area signals · research priority",
  interest_only: "Interest growing · development unconfirmed",
  no_sustained_growth: "No sustained search growth",
  insufficient_data: "Insufficient history",
};
const NAMES = { locality_interest: "Public locality interest", rental_interest: "Public rental research", app_searches: "Searches inside this app" };
const change = (value?: number | null) => value == null ? "Unavailable" : `${value >= 0 ? "+" : ""}${value.toFixed(1)}%`;

export function DevelopmentPanel({ reports }: { reports: AreaDevelopment[] }) {
  if (!reports.length) return null;
  const ranked = reports.filter((r) => r.rank != null);
  return (
    <section className="space-y-3" aria-label="Search history and developing areas">
      <h2 className="text-lg font-semibold">Search history and developing-area signals</h2>
      <p className="text-sm text-slate-600">Measured history determines research priorities among your selected localities. AI reviews the evidence and suggests possible explanations.</p>
      {!ranked.length && <p className="rounded-lg bg-slate-100 p-3 text-sm text-slate-600">No locality currently has enough corroborated, sustained property-search growth to receive a priority rank.</p>}
      {reports.map((report) => (
        <article key={report.locality_key} className="space-y-4 rounded-xl border border-slate-200 bg-white p-5">
          <div>
            <h3 className="font-semibold">{report.rank != null ? `#${report.rank} · ` : ""}{report.locality}, {report.city}</h3>
            <p className="text-sm font-medium text-slate-700">{SIGNALS[report.signal]}</p>
            <p className="mt-1 text-sm text-slate-600">{report.recommendation}</p>
            <p className="mt-1 text-xs text-slate-500">Evidence score: {report.evidence_score == null ? "Unavailable" : `${report.evidence_score.toFixed(1)}/100`} · Data coverage: {report.coverage_pct}% · AI review: {report.ai_review}. The score is a research heuristic, not a probability or return forecast.</p>
          </div>
          <div className="grid gap-4 lg:grid-cols-3">
            {[...(report.public_interest ?? []), report.app_interest].map((signal) => <History key={signal.kind} signal={signal} />)}
          </div>
          <div className="text-sm">
            <p className="font-medium">Observed corroborating evidence</p>
            {Object.entries(report.observed_price_growth ?? {}).map(([kind, growth]) => (
              <p key={kind}>{kind}: {change(growth.value)} reported past annual price change · <a href={growth.sources?.[0]?.url ?? undefined} target="_blank" rel="noreferrer" className="text-blue-700 underline">Price evidence</a></p>
            ))}
            <p>{report.recent_positive_infrastructure} distinct recent positive infrastructure reports. Reports do not verify construction completion.</p>
          </div>
          <div>
            <h4 className="text-sm font-medium">Possible reasons · unconfirmed hypotheses</h4>
            {!report.hypotheses?.length && <p className="text-sm text-slate-500">No supported causal explanation available.</p>}
            <ul className="mt-2 space-y-2 text-sm">
              {(report.hypotheses ?? []).map((item, i) => (
                <li key={i} className="rounded-lg bg-slate-50 p-3">
                  <p>{item.explanation}</p>
                  <blockquote className="mt-1 text-xs text-slate-600">{item.evidence.value}</blockquote>
                  <a href={item.evidence.sources?.[0]?.url ?? undefined} target="_blank" rel="noreferrer" className="text-xs text-blue-700 underline">Cited news evidence</a>
                </li>
              ))}
            </ul>
          </div>
          {!!report.warnings?.length && <ul className="rounded-lg bg-amber-50 p-3 text-xs text-amber-900">{report.warnings.map((issue, i) => <li key={i}>{issue.operation}: {issue.message}</li>)}</ul>}
          <details className="text-xs text-slate-500">
            <summary className="cursor-pointer">Method, scores and limitations</summary>
            <p>Compares 13 complete weeks with the previous 13; priority ranking requires at least 15% quarter growth, at least 10% growth against the same 13 weeks a year earlier and positive price/news corroboration. At least 8 recent weeks must exceed the preceding mean. Current/incomplete weeks are excluded.</p>
            <p>Weights: rental interest 35, broad locality interest 15, app history 15, observed prices 15, infrastructure 20. Missing components are omitted and coverage is reported.</p>
            <p>Components: {Object.entries(report.score_breakdown ?? {}).map(([key, value]) => `${key} ${value.toFixed(1)}`).join(" · ")}</p>
            <ul>{(report.limitations ?? []).map((note) => <li key={note}>{note}</li>)}</ul>
          </details>
        </article>
      ))}
    </section>
  );
}

function History({ signal }: { signal: SearchMomentum }) {
  const history = (signal.history ?? []).slice(-52);
  const publicData = signal.unit === "relative_interest_0_100";
  const max = publicData ? 100 : Math.max(1, ...history.map((p) => p.value));
  const line = history.map((point, i) => `${i === 0 ? "M" : "L"}${20 + i / Math.max(1, history.length - 1) * 320},${90 - point.value / max * 75}`).join(" ");
  return (
    <div className="rounded-lg border border-slate-100 p-3 text-xs">
      <h4 className="font-medium">{NAMES[signal.kind]}</h4>
      <p className="text-slate-500">{signal.query} · {publicData ? `Relative interest 0–100 · ${signal.geo}` : "Distinct profiles per complete UTC week"}</p>
      {history.length > 1 ? (
        <svg viewBox="0 0 360 110" className="my-2 w-full" role="img" aria-label={`${NAMES[signal.kind]} weekly history`}>
          <title>{NAMES[signal.kind]}: last {history.length} complete weeks</title>
          <path d="M20,15 V90 H340" fill="none" stroke="#cbd5e1" />
          <text x="0" y="18" fontSize="9" fill="#64748b">{max}</text><text x="5" y="93" fontSize="9" fill="#64748b">0</text>
          <path d={line} fill="none" stroke="#0f766e" strokeWidth="2" />
          <text x="20" y="106" fontSize="9" fill="#64748b">{history[0].week}</text>
          <text x="340" y="106" textAnchor="end" fontSize="9" fill="#64748b">{history[history.length - 1].week}</text>
        </svg>
      ) : <p className="my-3 text-slate-500">{publicData ? "Public history unavailable." : "Collecting complete weekly history."}</p>}
      <p>Measured signal: {signal.signal}</p>
      {signal.previous_mean != null && signal.recent_mean != null && <p>Previous / recent 13-week means: {signal.previous_mean.toFixed(1)} / {signal.recent_mean.toFixed(1)}</p>}
      <p>Recent 13 weeks vs previous 13: <strong>{change(signal.quarter_change_pct)}</strong></p>
      <p>Same period last year: <strong>{change(signal.annual_change_pct)}</strong></p>
      <p className="mt-1 text-slate-500">{signal.note}</p>
      {signal.sample_size != null && <p>{signal.sample_size} distinct profiles in the last 26 complete weeks.</p>}
      {signal.retrieved_at && <p className="mt-1 text-slate-500">Provider retrieval: {signal.retrieved_at}</p>}
      {signal.source?.url && <a href={signal.source.url} target="_blank" rel="noreferrer" className="text-blue-700 underline">Google Trends source</a>}
      {!!history.length && <details className="mt-2"><summary className="cursor-pointer">Weekly observations ({signal.history?.length})</summary><table className="mt-1 w-full text-left"><thead><tr><th>Week</th><th>{publicData ? "Interest index" : "Profiles"}</th></tr></thead><tbody>{signal.history?.map((p) => <tr key={p.week}><td>{p.week}</td><td>{p.value}</td></tr>)}</tbody></table></details>}
    </div>
  );
}

import type { components } from "../../api/schema";

export function RiskCard({ report }: { report: components["schemas"]["RiskReport"] }) {
  return <section className="space-y-3 rounded-xl border border-slate-200 bg-white p-4">
    <h2 className="font-semibold">Risk evidence screening</h2>
    <p className="text-xs text-slate-500">{report.note} Evidence coverage: {report.coverage_pct}%.</p>
    <div className="grid gap-4 sm:grid-cols-3">{report.indicators.map(item => <div key={item.kind}>
      <h3 className="font-medium capitalize">{item.kind}: {item.status === "unknown" ? "Unknown" : `Reported concern (${item.score}/100)`}</h3>
      <p className="text-xs text-slate-600">{item.next_step}</p>
      {(item.evidence ?? []).map((text, index) => <p className="mt-2 text-xs" key={index}>
        {item.sources?.[index]?.url ? <a className="underline" href={item.sources[index].url!} target="_blank" rel="noreferrer">{text}</a> : text}
      </p>)}
    </div>)}</div>
  </section>;
}

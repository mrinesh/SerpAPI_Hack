import { Link, useSearchParams } from "react-router";
import { describeError } from "../api/client";
import { useCompare } from "../api/hooks";
import { Notice } from "../components/Notice";
import { FlagChips } from "../components/run/FlagChips";
import { accessLine } from "../components/run/areaText";
import { SourcedValue } from "../components/SourcedValue";
import { bestIndices, comparisonRows } from "../lib/comparison";
import { formatInr } from "../lib/money";

export function ComparePage() {
  const [params] = useSearchParams();
  const ids = params.getAll("ids");
  const query = useCompare(ids);
  if (ids.length < 2 || ids.length > 4 || new Set(ids).size !== ids.length)
    return <p>Select 2?4 distinct properties on the <Link className="underline" to="/saved">Saved page</Link>.</p>;
  if (query.error) return <Notice tone="error">{describeError(query.error)}</Notice>;
  if (!query.data) return <p>Loading comparison?</p>;
  const properties = query.data.properties;
  const sameProfile = new Set(properties.map(p => p.profile_id)).size === 1;
  const scoreWinners = sameProfile ? bestIndices(properties.map(p => p.recommendation?.score), "max") : [];
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Compare properties</h1>
      <p className="text-sm text-slate-600">Latest stored search for each property. Green highlights the lowest cost or highest value in a row; missing data is excluded. These are estimates, before costs. Scores depend on the search profile.</p>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-sm">
          <thead><tr><th className="p-3 text-left">Measure</th>{properties.map(p => (
            <th key={p.listing.id} className="min-w-60 border p-3 text-left">
              <Link className="underline" to={`/runs/${p.run_id}/properties/${p.listing.id}`}>{p.listing.name}</Link>
              <p className="font-normal text-slate-500">{p.listing.property_type.value} ? {p.listing.locality.value}</p>
              <Link className="text-xs font-normal underline" to={`/runs/${p.run_id}`}>View source search</Link>
            </th>
          ))}</tr></thead>
          <tbody>
            {comparisonRows.map(row => {
              const facts = properties.map(row.fact);
              const winners = bestIndices(facts.map(f => typeof f?.value === "number" ? f.value : null), row.direction);
              return <tr key={row.label}><th className="border p-3 text-left">{row.label}</th>{facts.map((fact, i) => (
                <td key={properties[i].listing.id} className={`border p-3 ${winners.includes(i) ? "bg-emerald-50" : ""}`}>
                  <dl><SourcedValue label={row.label} fact={fact} format={value => typeof value === "number"
                    ? row.unit === "inr" ? formatInr(value) : `${value.toFixed(1)} ${row.unit}` : String(value)} /></dl>
                </td>
              ))}</tr>;
            })}
            <tr><th className="border p-3 text-left">Match score</th>{properties.map((p, i) => (
              <td key={p.listing.id} className={`border p-3 ${scoreWinners.includes(i) ? "bg-emerald-50" : ""}`}>{p.recommendation?.score ?? "?"}{p.recommendation && "/100"}</td>
            ))}</tr>
            <tr><th className="border p-3 text-left">Amenity access</th>{properties.map(p => <td key={p.listing.id} className="border p-3">{accessLine(p.recommendation?.access) || "Unknown"}</td>)}</tr>
            <tr><th className="border p-3 text-left">Quality flags</th>{properties.map(p => <td key={p.listing.id} className="border p-3"><FlagChips flags={p.verification?.flags ?? []} /></td>)}</tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}

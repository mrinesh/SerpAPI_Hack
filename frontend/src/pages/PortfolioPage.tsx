import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router";
import { apiFetch, ApiError, describeError } from "../api/client";
import type { components } from "../api/schema";
import { Notice } from "../components/Notice";
import { formatInr } from "../lib/money";

type Holding = components["schemas"]["Holding"];
type HoldingIn = components["schemas"]["HoldingIn"];
type Summary = components["schemas"]["PortfolioSummary"];
const FIELDS = [
  ["purchase_price_inr", "Purchase price (INR)"], ["acquisition_costs_inr", "Acquisition costs (INR)"],
  ["current_value_inr", "Your current valuation (INR, optional)"], ["outstanding_loan_inr", "Outstanding loan (INR)"],
  ["monthly_rent_inr", "Monthly rent (INR)"], ["monthly_expenses_inr", "Monthly expenses (INR)"],
  ["monthly_emi_inr", "Monthly EMI (INR)"],
] as const;
const inputClass = "mt-1 w-full rounded-md border border-slate-300 p-2 text-sm";

export function PortfolioPage() {
  const cache = useQueryClient();
  const [params] = useSearchParams();
  const [editing, setEditing] = useState<Holding | null>(null);
  const [revision, setRevision] = useState(0);
  const query = useQuery({ queryKey: ["portfolio"], queryFn: () => apiFetch<Summary>("/portfolio") });
  const save = useMutation({ mutationFn: (data: HoldingIn) => apiFetch<Holding>(editing ? `/portfolio/${editing.id}` : "/portfolio", {
    method: editing ? "PUT" : "POST", body: JSON.stringify(data),
  }), onSuccess: () => { cache.invalidateQueries({ queryKey: ["portfolio"] }); setEditing(null); setRevision(r => r + 1); } });
  const remove = useMutation({ mutationFn: (id: string) => apiFetch<void>(`/portfolio/${id}`, { method: "DELETE" }),
    onSuccess: () => cache.invalidateQueries({ queryKey: ["portfolio"] }) });
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const amounts = Object.fromEntries(FIELDS.map(([key]) => [key,
      key === "current_value_inr" && !form.get(key) ? null : Number(form.get(key) || 0)]));
    save.mutate({ ...amounts, name: String(form.get("name")), acquired_on: String(form.get("acquired_on")),
      valued_on: String(form.get("valued_on")) || null, note: String(form.get("note")) || null,
      listing_id: editing?.listing_id ?? params.get("listing_id") } as HoldingIn);
  }
  const data = query.data;
  return <div className="space-y-6">
    <header><h1 className="text-2xl font-semibold">Portfolio tracker</h1><p className="text-sm text-slate-600">Record your actual purchases, costs and valuations. Listing asking prices are not automatic valuations.</p></header>
    {query.error && <Notice tone="error">{describeError(query.error)}</Notice>}
    {data && <section className="rounded-xl border bg-white p-4 text-sm">
      <p>{data.holdings.length} holdings · Cost {formatInr(data.invested_cost_inr)} · Monthly cash flow {formatInr(data.monthly_cash_flow_inr)}</p>
      <p>Valued {data.valued_holdings}/{data.holdings.length} · Value {data.current_value_inr == null ? "Unknown" : formatInr(data.current_value_inr)} · Equity {data.equity_inr == null ? "Unknown" : formatInr(data.equity_inr)}</p>
      <p className="mt-2 text-xs text-slate-500">{data.note}</p>
    </section>}
    <div className="grid gap-3 sm:grid-cols-2">{data?.holdings.map(item => <article className="space-y-2 rounded-xl border bg-white p-4 text-sm" key={item.id}>
      <h2 className="font-semibold">{item.name}</h2>
      <p>Acquired {item.acquired_on} · Cost {formatInr(item.purchase_price_inr + (item.acquisition_costs_inr ?? 0))}</p>
      <p>Value {item.current_value_inr == null ? "Unknown" : `${formatInr(item.current_value_inr)} (${item.valued_on})`}</p>
      <p>Equity {item.equity_inr == null ? "Unknown" : formatInr(item.equity_inr)} · Cash flow {formatInr(item.monthly_cash_flow_inr)}/month</p>
      <p>Net operating yield on cost: {item.net_yield_on_cost_pct}% (before financing and taxes)</p>
      {item.note && <p>{item.note}</p>}
      {item.listing_id && <Link className="underline" to={`/properties/${item.listing_id}`}>Research snapshot</Link>}
      <div className="flex gap-4"><button className="underline" onClick={() => { setEditing(item); save.reset(); }}>Edit</button><button disabled={remove.isPending} className="text-red-700 underline" onClick={() => remove.mutate(item.id)}>Remove</button></div>
    </article>)}</div>
    {remove.error && <Notice tone="error">{describeError(remove.error)}</Notice>}
    <form key={`${editing?.id ?? "new"}-${revision}`} onSubmit={submit} className="space-y-4 rounded-xl border bg-white p-5">
      <h2 className="font-semibold">{editing ? "Edit holding" : "Add owned property"}</h2>
      {save.error && <Notice tone="error">{save.error instanceof ApiError ? Object.values(save.error.fieldErrors).join("; ") || save.error.message : describeError(save.error)}</Notice>}
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="text-sm">Name<input className={inputClass} name="name" required maxLength={160} defaultValue={editing?.name} /></label>
        <label className="text-sm">Acquisition date<input className={inputClass} name="acquired_on" type="date" required defaultValue={editing?.acquired_on} /></label>
        {FIELDS.map(([key, label]) => <label className="text-sm" key={key}>{label}<input className={inputClass} name={key} type="number" min={key === "purchase_price_inr" || key === "current_value_inr" ? 1 : 0} step="any" required={key === "purchase_price_inr"} defaultValue={editing?.[key] ?? (key === "current_value_inr" || key === "purchase_price_inr" ? "" : 0)} /></label>)}
        <label className="text-sm">Valuation date (with valuation)<input className={inputClass} type="date" name="valued_on" defaultValue={editing?.valued_on ?? ""} /></label>
      </div>
      <label className="block text-sm">Notes<textarea className={inputClass} name="note" maxLength={2000} defaultValue={editing?.note ?? ""} /></label>
      <button disabled={save.isPending} className="rounded-md bg-slate-900 px-4 py-2 text-sm text-white">{save.isPending ? "Saving…" : "Save holding"}</button>
      {editing && <button type="button" className="ml-3 text-sm underline" onClick={() => { setEditing(null); save.reset(); }}>Cancel edit</button>}
    </form>
  </div>;
}

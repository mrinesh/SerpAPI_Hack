import { useMutation } from "@tanstack/react-query";
import type { FormEvent } from "react";
import { apiFetch, ApiError, describeError } from "../api/client";
import type { components } from "../api/schema";
import { Notice } from "../components/Notice";
import { formatInr } from "../lib/money";

type Input = components["schemas"]["ScenarioIn"];
type Result = components["schemas"]["ScenarioResult"];
const FIELDS = [
  ["purchase_price_inr", "Purchase price (INR)", 10000000, 1, 1e12],
  ["down_payment_pct", "Down payment (%)", 20, 0, 100],
  ["purchase_cost_pct", "Purchase costs (%)", 5, 0, 50],
  ["loan_interest_pct", "Fixed annual loan interest (%)", 8.5, 0, 50],
  ["loan_years", "Loan term (years)", 20, 1, 40],
  ["hold_years", "Hold before exit (years)", 5, 1, 40],
  ["monthly_rent_inr", "Starting monthly rent (INR)", 30000, 0, 1e9],
  ["vacancy_pct", "Vacancy (%)", 5, 0, 100],
  ["monthly_expenses_inr", "Monthly expenses (INR)", 3000, 0, 1e9],
  ["annual_rent_growth_pct", "Assumed annual rent growth (%)", 0, -100, 100],
  ["annual_price_growth_pct", "Assumed annual price growth (%)", 0, -100, 100],
  ["exit_cost_pct", "Exit costs (%)", 2, 0, 50],
] as const;

export function ScenarioPage() {
  const calculation = useMutation({ mutationFn: (data: Input) => apiFetch<Result>("/scenarios", { method: "POST", body: JSON.stringify(data) }) });
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    calculation.mutate(Object.fromEntries(FIELDS.map(([key]) => [key, Number(form.get(key))])) as Input);
  }
  const data = calculation.data;
  return <div className="space-y-5">
    <header><h1 className="text-2xl font-semibold">Investment scenario calculator</h1><p className="text-sm text-slate-600">Change loan, rent, costs and exit assumptions. The starting values are examples; enter your own terms.</p></header>
    <form onSubmit={submit} className="space-y-4 rounded-xl border bg-white p-5">
      <div className="grid gap-4 sm:grid-cols-3">{FIELDS.map(([key, label, value, min, max]) => <label key={key} className="text-sm">{label}<input name={key} type="number" step={key.endsWith("years") ? 1 : "any"} min={min} max={max} required defaultValue={value} className="mt-1 w-full rounded-md border border-slate-300 p-2" /></label>)}</div>
      <button disabled={calculation.isPending} className="rounded-md bg-slate-900 px-4 py-2 text-sm text-white">{calculation.isPending ? "Calculating…" : "Calculate scenario"}</button>
    </form>
    {calculation.error && <Notice tone="error">{calculation.error instanceof ApiError ? Object.values(calculation.error.fieldErrors).join("; ") || calculation.error.message : describeError(calculation.error)}</Notice>}
    {data && <section className="space-y-3 rounded-xl border bg-white p-5 text-sm">
      <h2 className="font-semibold">Calculated scenario for the submitted assumptions</h2>
      <p>Initial cash {formatInr(data.initial_cash_inr)} · Loan {formatInr(data.loan_principal_inr)} · Monthly EMI {formatInr(data.monthly_emi_inr)}</p>
      <p>Exit value {formatInr(data.exit_value_inr)} · Debt at exit {formatInr(data.exit_loan_balance_inr)} · Net exit proceeds {formatInr(data.net_exit_proceeds_inr)}</p>
      <p>Cumulative cash flow {formatInr(data.cumulative_cash_flow_inr)} · Total profit {formatInr(data.total_profit_inr)} · Holding-period equity return {data.equity_return_pct}%</p>
      <p className="text-xs text-slate-500">{data.note}</p>
      <details className="text-xs"><summary className="cursor-pointer">Submitted assumptions</summary>{Object.entries(data.assumptions).map(([key,value]) => <p key={key}>{key.replaceAll("_", " ")}: {value}</p>)}</details>
      <div className="overflow-auto"><table className="w-full text-left text-xs"><thead><tr>{["Year", "Rent", "Expenses", "Loan payments", "Interest", "Principal", "Debt left", "Cash flow"].map(title => <th className="p-2" key={title}>{title}</th>)}</tr></thead><tbody>{data.years.map(year => <tr className="border-t" key={year.year}><td className="p-2">{year.year}</td>{[year.rent_inr, year.expenses_inr, year.loan_payments_inr, year.interest_inr, year.principal_inr, year.balance_inr, year.cash_flow_inr].map((v,i) => <td className="p-2 whitespace-nowrap" key={i}>{formatInr(v)}</td>)}</tr>)}</tbody></table></div>
    </section>}
  </div>;
}

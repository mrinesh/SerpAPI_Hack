import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { AccountGate } from "../components/AccountGate";
import { draftPatch } from "../components/profile/LanguagePrefill";
import { RiskCard } from "../components/run/RiskCard";
import { PortfolioPage } from "./PortfolioPage";
import { ScenarioPage } from "./ScenarioPage";

describe("P2 screens", () => {
  it("does not render private children when login is required", () => {
    const cache = new QueryClient({ defaultOptions: { queries: { staleTime: Infinity, retry: false } } });
    cache.setQueryData(["auth"], { enabled: true, user: null });
    const html = renderToStaticMarkup(<QueryClientProvider client={cache}><AccountGate><p>Secret portfolio</p></AccountGate></QueryClientProvider>);
    expect(html).toContain("Sign in");
    expect(html).not.toContain("Secret portfolio");
    expect(html).toContain('type="password"');
  });
  it("waits for private cache cleanup before rendering an authenticated workspace", () => {
    const cache = new QueryClient({ defaultOptions: { queries: { staleTime: Infinity } } });
    cache.setQueryData(["auth"], { enabled: true, user: { id: "bob", username: "bob" } });
    cache.setQueryData(["portfolio"], { note: "Alice's previous workspace" });
    const html = renderToStaticMarkup(<QueryClientProvider client={cache}><AccountGate><p>Alice's previous workspace</p></AccountGate></QueryClientProvider>);
    expect(html).toContain("Loading your workspace");
    expect(html).not.toContain("Alice");
  });
  it("shows unknown risk as unknown, with due diligence", () => {
    const html = renderToStaticMarkup(<RiskCard report={{ coverage_pct: 0, note: "No matching report means unknown, not safe.", indicators: [
      { kind: "legal", status: "unknown", score: null, next_step: "Verify title with a lawyer" },
    ] }} />);
    expect(html).toContain("Unknown");
    expect(html).toContain("Verify title");
    expect(html).not.toContain("0/100");
  });
  it("renders portfolio valuations and record controls", () => {
    const cache = new QueryClient({ defaultOptions: { queries: { staleTime: Infinity } } });
    cache.setQueryData(["portfolio"], { holdings: [], invested_cost_inr: 0, valued_holdings: 0,
      current_value_inr: null, equity_inr: null, monthly_cash_flow_inr: 0, note: "Manual valuations" });
    const html = renderToStaticMarkup(<QueryClientProvider client={cache}><MemoryRouter><PortfolioPage /></MemoryRouter></QueryClientProvider>);
    expect(html).toContain("Value Unknown");
    expect(html).toContain("Acquisition date");
    expect(html).toContain("Save holding");
  });
  it("exposes scenario assumptions as editable inputs", () => {
    const html = renderToStaticMarkup(<QueryClientProvider client={new QueryClient()}><ScenarioPage /></QueryClientProvider>);
    expect(html).toContain("Calculate scenario");
    expect(html).toContain("Vacancy (%)");
    expect(html).toContain("Assumed annual price growth");
    expect(html).toContain('name="exit_cost_pct"');
  });
  it("applies only recognized language fields without inventing defaults", () => {
    expect(draftPatch({ budget_max_inr: 9000000, target_roi_pct: 0 })).toEqual({
      budgetMax: { amount: "90", unit: "lakh" }, targetRoi: "0",
    });
    expect(draftPatch({})).toEqual({});
  });
});

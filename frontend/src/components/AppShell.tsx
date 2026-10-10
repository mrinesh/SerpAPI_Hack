import { NavLink, Outlet } from "react-router";

import { useAlerts, useBudget, useHealth } from "../api/hooks";

const NAV = [
  { to: "/", label: "Profiles", end: true },
  { to: "/saved", label: "Saved" },
  { to: "/portfolio", label: "Portfolio" },
  { to: "/scenarios", label: "Scenarios" },
  { to: "/compare", label: "Compare" },
  { to: "/alerts", label: "Alerts" },
];

export function AppShell() {
  const unread = useAlerts(true);
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center gap-6 px-4 py-3">
          <span className="font-semibold tracking-tight">Realty Intel</span>
          <nav className="flex gap-1 text-sm">
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `rounded-md px-3 py-1.5 ${isActive ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100"}`
                }
              >
                {item.label}{item.to === "/alerts" && (unread.data?.length ?? 0) > 0 && (
                  <span className="ml-1 rounded-full bg-amber-100 px-1.5 text-amber-900" aria-label={`${unread.data!.length} unread alerts`}>{unread.data!.length}</span>
                )}
              </NavLink>
            ))}
          </nav>
          <BackendStatus />
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8">
        <Outlet />
      </main>
    </div>
  );
}

/** Provider modes and the SerpApi search budget (CHECKLIST I-05). */
function BackendStatus() {
  const { data, isError } = useHealth();
  const budget = useBudget();
  if (isError) return <span className="ml-auto text-xs text-red-600">backend offline</span>;
  if (!data) return null;
  const left = budget.data?.account_searches_left;
  return (
    <span className="ml-auto flex gap-2 text-xs text-slate-600">
      <span className="rounded-full bg-slate-100 px-3 py-1">
        {data.city} · SerpApi {data.serpapi_mode} · LLM {data.llm_mode}
      </span>
      {budget.data && (
        <span
          className="rounded-full bg-slate-100 px-3 py-1"
          title="Live searches this app made this month, and searches left on the SerpApi account"
        >
          {budget.data.used_this_month} searches used
          {left != null && ` · ${left} left`}
        </span>
      )}
    </span>
  );
}

import { NavLink, Outlet } from "react-router";

import { useHealth } from "../api/hooks";

const NAV = [
  { to: "/", label: "Profiles", end: true },
  { to: "/saved", label: "Saved" },
  { to: "/compare", label: "Compare" },
  { to: "/alerts", label: "Alerts" },
];

export function AppShell() {
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
                {item.label}
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

/** Shows which provider modes the backend runs in. The search budget chip joins it in I-05. */
function BackendStatus() {
  const { data, isError } = useHealth();
  if (isError) return <span className="ml-auto text-xs text-red-600">backend offline</span>;
  if (!data) return null;
  return (
    <span className="ml-auto rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600">
      {data.city} · SerpApi {data.serpapi_mode} · LLM {data.llm_mode}
    </span>
  );
}

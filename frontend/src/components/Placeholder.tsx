import type { ReactNode } from "react";

interface PlaceholderProps {
  title: string;
  /** CHECKLIST.md IDs this screen is built under. */
  features: string[];
  children: ReactNode;
}

/** Stands in for a screen that is scaffolded but not built yet. */
export function Placeholder({ title, features, children }: PlaceholderProps) {
  return (
    <section className="rounded-xl border border-dashed border-slate-300 bg-white p-8">
      <div className="flex items-baseline justify-between gap-4">
        <h1 className="text-xl font-semibold">{title}</h1>
        <span className="font-mono text-xs text-slate-500">{features.join(" · ")}</span>
      </div>
      <div className="mt-3 space-y-2 text-sm text-slate-600">{children}</div>
    </section>
  );
}

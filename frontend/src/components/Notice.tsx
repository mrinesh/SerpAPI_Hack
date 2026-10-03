import type { ReactNode } from "react";

const TONES = {
  error: "border-red-200 bg-red-50 text-red-800",
  info: "border-slate-200 bg-slate-50 text-slate-700",
};

/** An inline banner for errors and status messages. */
export function Notice({ tone, children }: { tone: keyof typeof TONES; children: ReactNode }) {
  return (
    <div role={tone === "error" ? "alert" : "status"} className={`rounded-md border px-4 py-3 text-sm ${TONES[tone]}`}>
      {children}
    </div>
  );
}

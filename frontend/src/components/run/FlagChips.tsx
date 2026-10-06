import type { QualityFlag } from "../../api/types";

const FLAG_LABELS: Record<QualityFlag["kind"], string> = {
  too_good_to_be_true: "Too good to be true",
  missing_price: "No price",
  missing_size: "No size",
  duplicate: "Duplicate",
  location_mismatch: "Location mismatch",
};

const FLAG_STYLES: Record<QualityFlag["severity"], string> = {
  high: "border-amber-300 bg-amber-50 text-amber-800",
  medium: "border-amber-200 bg-amber-50 text-amber-700",
  low: "border-slate-200 bg-slate-50 text-slate-600",
};

/** F-12 quality flags; the reason is the tooltip (high ones are also listed as mismatches). */
export function FlagChips({ flags }: { flags: QualityFlag[] }) {
  if (flags.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-1">
      {flags.map((flag) => (
        <span
          key={flag.kind}
          title={flag.reason}
          className={`rounded-full border px-2 py-0.5 font-medium ${FLAG_STYLES[flag.severity]}`}
        >
          {FLAG_LABELS[flag.kind]}
        </span>
      ))}
    </div>
  );
}

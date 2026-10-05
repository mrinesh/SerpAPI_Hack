import { useState, type ReactNode } from "react";

import type { Listing, Portal, ProfileOptions, QualityFlag, SaleStatus, Verification } from "../../api/types";
import { formatInr } from "../../lib/money";
import { groupCandidates } from "./groupCandidates";

const PORTAL_LABELS: Record<Portal, string> = {
  "99acres": "99acres",
  magicbricks: "MagicBricks",
  nobroker: "NoBroker",
  google_maps: "Google Maps",
};

const STATUS_LABELS: Record<SaleStatus, string> = {
  ready_to_move: "Ready to move",
  under_construction: "Under construction",
  resale: "Resale",
  new_launch: "New launch",
};

type Tab = "priced" | "projects" | "filtered";

/** Discovered candidates with relevance checks. Rejects remain visible with their reasons. */
export function CandidateList({ listings, options, verifications }: {
  listings: Listing[]; options: ProfileOptions; verifications: Verification[];
}) {
  const groups = groupCandidates(listings, verifications);
  const { priced, projects, filtered } = groups;
  const checks = new Map(verifications.map((check) => [check.listing_id, check]));
  const [tab, setTab] = useState<Tab>(priced.length > 0 ? "priced" : projects.length > 0 ? "projects" : "filtered");
  const shown = groups[tab];
  const typeLabel = (value: string | null | undefined) =>
    options.segments.flatMap((s) => s.property_types).find((t) => t.value === value)?.label ?? value;
  const localityName = (slug: string | null | undefined) =>
    options.localities.find((l) => l.slug === slug)?.name ?? slug;

  if (listings.length === 0) {
    return <p className="text-sm text-slate-500">No candidates found.</p>;
  }

  return (
    <section className="space-y-3">
      <div className="flex items-center gap-2" role="tablist">
        <TabButton active={tab === "priced"} onClick={() => setTab("priced")}>
          Priced entries ({priced.length})
        </TabButton>
        <TabButton active={tab === "projects"} onClick={() => setTab("projects")}>
          Projects on Google Maps ({projects.length})
        </TabButton>
        <TabButton active={tab === "filtered"} onClick={() => setTab("filtered")}>
          Filtered out ({filtered.length})
        </TabButton>
      </div>
      <p className="text-xs text-slate-500">
        {tab === "filtered"
          ? "Candidates that fail your criteria. Their source links and rejection reasons are kept for review."
          : tab === "priced"
          ? "Prices quoted on the portals' search pages. The link opens the page that quoted it, not a single unit."
          : "Housing projects in the locality from Google Maps. No price is quoted for these yet."}
      </p>
      {shown.length === 0 && <p className="text-sm text-slate-500">No candidates in this view.</p>}
      <ul className="divide-y divide-slate-100 rounded-xl border border-slate-200 bg-white">
        {shown.map((listing) => (
          <li key={listing.id} className="grid gap-1 px-4 py-3 sm:grid-cols-[1fr_auto]">
            <div className="min-w-0">
              <p className="truncate font-medium" title={listing.name}>
                {listing.name}
              </p>
              <p className="text-xs text-slate-500">
                {[
                  typeLabel(listing.property_type.value),
                  localityName(listing.locality.value),
                  listing.bedrooms.value != null && `${listing.bedrooms.value} BHK`,
                  listing.size_sqft.value != null &&
                    `${Math.round(listing.size_sqft.value)} sq ft${listing.size_sqft.method === "computed" ? " (computed)" : ""}`,
                  listing.status.value && STATUS_LABELS[listing.status.value],
                  listing.rating != null && `${listing.rating}★ (${listing.reviews} reviews)`,
                ]
                  .filter(Boolean)
                  .join(" · ")}
              </p>
              {listing.evidence && (
                <p className="mt-1 line-clamp-2 text-xs text-slate-400" title={listing.evidence}>
                  “{listing.evidence}”
                </p>
              )}
              {checks.has(listing.id)
                ? <VerificationSummary verification={checks.get(listing.id)!} />
                : <p className="mt-2 text-xs text-slate-500">Not AI-checked</p>}
            </div>
            <div className="text-left sm:text-right">
              {listing.price_inr.value != null && (
                <p className="font-semibold" title={listing.price_inr.note ?? undefined}>
                  {formatInr(listing.price_inr.value)}
                  {listing.price_inr.note && <span className="text-slate-400"> *</span>}
                </p>
              )}
              {listing.price_per_sqft.value != null && (
                <p className="text-xs text-slate-500">
                  ₹{listing.price_per_sqft.value.toLocaleString("en-IN")}/sq ft
                </p>
              )}
              {listing.url && (
                <a
                  href={listing.url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs text-slate-600 underline hover:text-slate-900"
                >
                  {PORTAL_LABELS[listing.portal]} ↗
                </a>
              )}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

const VERDICT_LABELS: Record<Verification["verdict"], string> = {
  strong: "Strong match", partial: "Partial match", weak: "Weak match", reject: "Filtered out",
};

function VerificationSummary({ verification }: { verification: Verification }) {
  const rejected = verification.verdict === "reject";
  return (
    <div className="mt-3 space-y-2 text-xs">
      <p className={rejected ? "font-medium text-red-700" : "font-medium text-slate-700"}>
        {VERDICT_LABELS[verification.verdict]} · Relevance {verification.match_score}/100
        {" · "}{Math.round(verification.confidence * 100)}% confidence
      </p>
      <FlagChips flags={verification.flags ?? []} />
      <CheckReasons label="Matched" reasons={verification.matched_criteria ?? []} />
      <CheckReasons label={rejected ? "Rejection reasons" : "Mismatches"} reasons={verification.mismatches ?? []} />
      <CheckReasons label="Missing or unconfirmed" reasons={verification.missing_data ?? []} />
    </div>
  );
}

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
function FlagChips({ flags }: { flags: QualityFlag[] }) {
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

function CheckReasons({ label, reasons }: { label: string; reasons: string[] }) {
  if (reasons.length === 0) return null;
  return (
    <div>
      <p className="font-medium text-slate-600">{label}</p>
      <ul className="list-disc space-y-0.5 pl-4 text-slate-500">
        {reasons.map((reason, index) => <li key={`${index}-${reason}`}>{reason}</li>)}
      </ul>
    </div>
  );
}

function TabButton(props: { active: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={props.active}
      onClick={props.onClick}
      className={`rounded-md px-3 py-1.5 text-sm ${props.active ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100"}`}
    >
      {props.children}
    </button>
  );
}

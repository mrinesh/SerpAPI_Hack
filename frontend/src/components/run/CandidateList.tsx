import { useState, type ReactNode } from "react";

import type { Listing, Portal, ProfileOptions, SaleStatus } from "../../api/types";
import { formatInr } from "../../lib/money";

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

type Tab = "priced" | "projects";

/** Candidates a discovery run found (F-02): not yet AI-checked or ranked. */
export function CandidateList({ listings, options }: { listings: Listing[]; options: ProfileOptions }) {
  const priced = listings.filter((l) => l.kind === "snippet_entry");
  const projects = listings.filter((l) => l.kind === "project");
  const [tab, setTab] = useState<Tab>(priced.length > 0 ? "priced" : "projects");
  const shown = tab === "priced" ? priced : projects;
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
      </div>
      <p className="text-xs text-slate-500">
        {tab === "priced"
          ? "Prices quoted on the portals' search pages. The link opens the page that quoted it, not a single unit."
          : "Housing projects in the locality from Google Maps. No price is quoted for these yet."}
      </p>
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

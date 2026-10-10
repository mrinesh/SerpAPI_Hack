import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { apiFetch, describeError } from "../../api/client";
import type { components } from "../../api/schema";
import type { ProfileFormState } from "./formState";
import { fromInr } from "../../lib/money";
import { Notice } from "../Notice";

type Draft = components["schemas"]["ProfileDraft"];
type Result = components["schemas"]["LanguageProfileResult"];
export function draftPatch(draft: Draft): Partial<ProfileFormState> {
  const patch: Partial<ProfileFormState> = {};
  if (draft.segment) { patch.segment = draft.segment; patch.propertyTypes = draft.property_types ?? []; if (draft.segment === "residential") patch.businessType = ""; }
  if (draft.localities?.length) patch.localities = draft.localities;
  if (draft.must_haves?.length) patch.mustHaves = draft.must_haves;
  if (draft.budget_min_inr != null) patch.budgetMin = fromInr(draft.budget_min_inr);
  if (draft.budget_max_inr != null) patch.budgetMax = fromInr(draft.budget_max_inr);
  if (draft.size_min_sqft != null) patch.sizeMin = String(draft.size_min_sqft);
  if (draft.size_max_sqft != null) patch.sizeMax = String(draft.size_max_sqft);
  if (draft.goal) patch.goal = draft.goal;
  if (draft.target_roi_pct != null) patch.targetRoi = String(draft.target_roi_pct);
  if (draft.risk_appetite) patch.riskAppetite = draft.risk_appetite;
  if (draft.business_type) patch.businessType = draft.business_type;
  return patch;
}

export function LanguagePrefill({ city, apply }: { city: string; apply: (patch: Partial<ProfileFormState>) => void }) {
  const [text, setText] = useState("");
  const parse = useMutation({ mutationFn: () => apiFetch<Result>("/profiles/parse-language", { method: "POST", body: JSON.stringify({ text, city }) }) });
  return <section className="space-y-3 rounded-xl border bg-white p-5">
    <label className="block text-sm font-medium" htmlFor="search-description">Describe your search (optional)</label>
    <textarea id="search-description" className="w-full rounded-md border border-slate-300 p-2 text-sm" maxLength={2000} value={text} onChange={event => { setText(event.target.value); parse.reset(); }} placeholder="Flat in Whitefield under 90 lakh, rental income, low risk, target ROI 6%, near metro" />
    <button type="button" disabled={!text.trim() || parse.isPending} className="rounded-md border px-3 py-2 text-sm disabled:opacity-50" onClick={() => parse.mutate()}>Review recognized criteria</button>
    {parse.error && <Notice tone="error">{describeError(parse.error)}</Notice>}
    {parse.data && <div className="space-y-2 text-xs text-slate-600"><p>{parse.data.note}</p>
      {Object.entries(parse.data.matched_phrases).map(([field, phrase]) => <p key={field}>{field.replaceAll("_", " ")}: “{phrase}”</p>)}
      {parse.data.unresolved.map(note => <p key={note}>{note}</p>)}
      <button type="button" className="rounded-md bg-slate-900 px-3 py-2 text-white" onClick={() => apply(draftPatch(parse.data!.draft))}>Apply recognized fields to form</button>
    </div>}
  </section>;
}

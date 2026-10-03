import { useState } from "react";
import { Link, useNavigate } from "react-router";

import { ApiError, describeError } from "../api/client";
import { useDeleteProfile, useProfileOptions, useProfiles, useStartRun } from "../api/hooks";
import type { InvestorProfile, ProfileOptions } from "../api/types";
import { Notice } from "../components/Notice";
import { formatInr } from "../lib/money";

/** Saved investor profiles, each a starting point for a property search (F-01). */
export function ProfilesPage() {
  const profiles = useProfiles();
  const options = useProfileOptions();
  const error = profiles.error ?? options.error;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Investor profiles</h1>
          <p className="text-sm text-slate-600">Your criteria. Each profile drives a property search.</p>
        </div>
        <Link
          to="/profiles/new"
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
        >
          New profile
        </Link>
      </div>

      {error ? (
        <Notice tone="error">{describeError(error)}</Notice>
      ) : !profiles.data || !options.data ? (
        <p className="text-sm text-slate-500">Loading…</p>
      ) : profiles.data.length === 0 ? (
        <Notice tone="info">No profiles yet. Create one to start finding properties.</Notice>
      ) : (
        <ul className="grid gap-4 md:grid-cols-2">
          {profiles.data.map((profile) => (
            <ProfileCard key={profile.id} profile={profile} options={options.data} />
          ))}
        </ul>
      )}
    </div>
  );
}

function ProfileCard({ profile, options }: { profile: InvestorProfile; options: ProfileOptions }) {
  const navigate = useNavigate();
  const startRun = useStartRun();
  const deleteProfile = useDeleteProfile();
  const [message, setMessage] = useState<string | null>(null);

  const segment = options.segments.find((s) => s.value === profile.segment);
  const typeLabels = profile.property_types.map(
    (t) => segment?.property_types.find((o) => o.value === t)?.label ?? t,
  );
  const localityNames = profile.localities.map(
    (slug) => options.localities.find((l) => l.slug === slug)?.name ?? slug,
  );
  const goal = options.goals.find((g) => g.value === profile.goal);
  const risk = options.risk_levels.find((r) => r.value === profile.risk_appetite);
  const budget =
    profile.budget_min_inr != null
      ? `${formatInr(profile.budget_min_inr)} – ${formatInr(profile.budget_max_inr)}`
      : `Up to ${formatInr(profile.budget_max_inr)}`;
  const size =
    profile.size_min_sqft != null || profile.size_max_sqft != null
      ? `${profile.size_min_sqft ?? "any"} – ${profile.size_max_sqft ?? "any"} sq ft`
      : null;

  const findProperties = () => {
    setMessage(null);
    startRun.mutate(profile.id, {
      onSuccess: (run) => navigate(`/runs/${run.id}`),
      onError: (error) =>
        setMessage(
          error instanceof ApiError && error.isNotImplemented
            ? `The search pipeline isn't built yet (CHECKLIST ${error.featureId}).`
            : describeError(error),
        ),
    });
  };

  const remove = () => {
    if (window.confirm(`Delete the profile "${profile.name}"?`)) {
      deleteProfile.mutate(profile.id, { onError: (error) => setMessage(describeError(error)) });
    }
  };

  return (
    <li className="flex flex-col gap-4 rounded-xl border border-slate-200 bg-white p-5">
      <div>
        <div className="flex items-start justify-between gap-3">
          <h2 className="font-semibold">{profile.name}</h2>
          <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs text-slate-600">
            {segment?.label ?? profile.segment}
          </span>
        </div>
        <p className="mt-1 text-sm text-slate-600">
          {typeLabels.join(", ")}
          {profile.business_type && ` · for a ${profile.business_type.toLowerCase()}`}
        </p>
      </div>

      <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
        <dt className="text-slate-500">Where</dt>
        <dd>{localityNames.join(", ")}</dd>
        <dt className="text-slate-500">Budget</dt>
        <dd>{budget}</dd>
        {size && (
          <>
            <dt className="text-slate-500">Size</dt>
            <dd>{size}</dd>
          </>
        )}
        <dt className="text-slate-500">Goal</dt>
        <dd>
          {goal?.label}: target {profile.target_roi_pct}% {goal?.measure_label.toLowerCase()}
          {profile.expected_growth_pct != null && `, assuming ${profile.expected_growth_pct}% growth`}
        </dd>
        <dt className="text-slate-500">Risk</dt>
        <dd>{risk?.label}</dd>
        {(profile.must_haves ?? []).length > 0 && (
          <>
            <dt className="text-slate-500">Must-haves</dt>
            <dd>{profile.must_haves?.join(", ")}</dd>
          </>
        )}
      </dl>

      {message && <Notice tone="info">{message}</Notice>}

      <div className="mt-auto flex gap-2">
        <button
          type="button"
          onClick={findProperties}
          disabled={startRun.isPending}
          className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
        >
          Find properties
        </button>
        <Link
          to={`/profiles/${profile.id}/edit`}
          className="rounded-md border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-100"
        >
          Edit
        </Link>
        <button
          type="button"
          onClick={remove}
          disabled={deleteProfile.isPending}
          className="ml-auto rounded-md px-3 py-1.5 text-sm text-red-700 hover:bg-red-50 disabled:opacity-50"
        >
          Delete
        </button>
      </div>
    </li>
  );
}

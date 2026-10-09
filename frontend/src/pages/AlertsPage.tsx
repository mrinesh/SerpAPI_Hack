import { useState } from "react";
import { Link } from "react-router";
import { describeError } from "../api/client";
import { useAlerts, useCheckAlerts, useProfiles, useReadAlert } from "../api/hooks";
import { Notice } from "../components/Notice";

export function AlertsPage() {
  const [unreadOnly, setUnreadOnly] = useState(false);
  const alerts = useAlerts(unreadOnly);
  const profiles = useProfiles();
  const check = useCheckAlerts();
  const read = useReadAlert();
  const error = alerts.error || check.error || read.error;
  return (
    <div className="space-y-5">
      <header className="flex flex-wrap justify-between gap-3">
        <div><h1 className="text-2xl font-semibold">Alerts</h1>
          <p className="text-sm text-slate-600">New verified matches and changes in quoted prices for your profiles.</p></div>
        <button className="rounded bg-slate-900 px-4 py-2 text-white disabled:opacity-50"
          disabled={check.isPending} onClick={() => check.mutate()}>
          {check.isPending ? "Checking profiles…" : "Check now"}
        </button>
      </header>
      <p className="text-xs text-slate-500">Checking refreshes each idle profile through the search pipeline. Live mode uses your search budget; replay uses recorded results.</p>
      <label className="flex gap-2 text-sm"><input type="checkbox" checked={unreadOnly} onChange={e => setUnreadOnly(e.target.checked)} />Unread only</label>
      {error && <Notice tone="error">{describeError(error)}</Notice>}
      {check.data && <Notice tone="info">Checked {check.data.checked_profiles ?? 0} profiles; skipped {check.data.skipped_profiles ?? 0} active profiles; {check.data.alerts?.length ?? 0} new alerts.
        {check.data.errors?.map(issue => <p key={issue.profile_id}>{profiles.data?.find(p => p.id === issue.profile_id)?.name ?? issue.profile_id}: {issue.message}</p>)}
      </Notice>}
      {!alerts.data ? <p>Loading…</p> : alerts.data.length === 0 ? <p>No {unreadOnly ? "unread " : ""}alerts.</p>
        : <ul className="space-y-3">{alerts.data.map(alert => (
          <li key={alert.id} className={`space-y-2 rounded-xl border p-4 ${alert.read_at ? "border-slate-200" : "border-amber-200 bg-amber-50"}`}>
            <p className="text-xs text-slate-500">{profiles.data?.find(p => p.id === alert.profile_id)?.name ?? "Profile"} · {new Date(alert.created_at).toLocaleString("en-IN")}</p>
            <p className="font-medium">{alert.kind === "price_drop" ? "Quoted price drop" : "New match"}</p>
            <p>{alert.message}</p>
            <div className="flex gap-4 text-sm">
              <Link className="underline" to={`/properties/${alert.listing_id}`}>View property and sources</Link>
              {!alert.read_at && <button disabled={read.isPending} className="underline" onClick={() => read.mutate(alert.id)}>Mark read</button>}
            </div>
          </li>
        ))}</ul>}
    </div>
  );
}

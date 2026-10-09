import { useState } from "react";
import { Link } from "react-router";
import { describeError } from "../api/client";
import { useSaved, useSave, useUnsave } from "../api/hooks";
import type { SavedProperty } from "../api/types";
import { Notice } from "../components/Notice";
import { formatInr } from "../lib/money";

export function SavedPage() {
  const saved = useSaved();
  const [selected, setSelected] = useState<string[]>([]);
  const ids = selected.filter(id => saved.data?.some(item => item.listing.id === id));
  if (saved.error) return <Notice tone="error">{describeError(saved.error)}</Notice>;
  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-semibold">Saved properties</h1>
      <p className="text-sm text-slate-600">Keep notes and select 2?4 properties to compare.</p>
      <Link to={`/compare?${new URLSearchParams(ids.map(id => ["ids", id]))}`}
        aria-disabled={ids.length < 2} onClick={e => { if (ids.length < 2) e.preventDefault(); }}
        className={`inline-block rounded bg-slate-900 px-4 py-2 text-white ${ids.length < 2 ? "opacity-40" : ""}`}>
        Compare selected ({ids.length}/4)
      </Link>
      {!saved.data ? <p>Loading?</p> : saved.data.length === 0
        ? <p>No saved properties yet. Save a property from your search results.</p>
        : <ul className="space-y-3">{saved.data.map(item => (
          <SavedCard key={item.listing.id} item={item} selected={ids.includes(item.listing.id)}
            disabled={ids.length >= 4 && !ids.includes(item.listing.id)}
            toggle={() => setSelected(ids.includes(item.listing.id)
              ? ids.filter(id => id !== item.listing.id) : [...ids, item.listing.id])} />
        ))}</ul>}
    </div>
  );
}

function SavedCard({ item, selected, disabled, toggle }: {
  item: SavedProperty; selected: boolean; disabled: boolean; toggle: () => void;
}) {
  const [note, setNote] = useState(item.note ?? "");
  const save = useSave();
  const remove = useUnsave();
  const error = save.error || remove.error;
  return (
    <li className="space-y-2 rounded-xl border border-slate-200 bg-white p-4">
      <label className="flex gap-3 items-center">
        <input type="checkbox" checked={selected} disabled={disabled} onChange={toggle} />
        <span>Select for comparison</span>
      </label>
      <Link className="font-medium underline" to={`/properties/${item.listing.id}`}>{item.listing.name}</Link>
      <p>{item.listing.price_inr.value != null ? formatInr(item.listing.price_inr.value) : "Price unknown"}</p>
      <label className="block text-sm">Your notes
        <textarea maxLength={2000} value={note} onChange={e => setNote(e.target.value)}
          className="mt-1 block w-full rounded border border-slate-300 p-2" />
      </label>
      <div className="flex gap-4 text-sm">
        <button disabled={save.isPending || remove.isPending} onClick={() => save.mutate({ listing_id: item.listing.id, note })}
          className="underline">Save notes</button>
        <button disabled={remove.isPending || save.isPending} onClick={() => remove.mutate(item.listing.id)}
          className="underline">Remove</button>
        {save.isSuccess && !save.isPending && <span role="status">Notes saved</span>}
      </div>
      {error && <Notice tone="error">{describeError(error)}</Notice>}
    </li>
  );
}

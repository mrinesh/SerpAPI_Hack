import { describeError } from "../api/client";
import { useSaved, useSave, useUnsave } from "../api/hooks";

export function SaveButton({ listingId }: { listingId: string }) {
  const saved = useSaved();
  const save = useSave();
  const remove = useUnsave();
  const selected = saved.data?.some(item => item.listing.id === listingId) ?? false;
  const error = saved.error || save.error || remove.error;
  return (
    <div className="my-2 text-xs">
      <button type="button" aria-pressed={selected}
        disabled={!saved.data || save.isPending || remove.isPending}
        className="rounded border border-slate-300 px-3 py-1 disabled:opacity-50"
        onClick={() => selected ? remove.mutate(listingId) : save.mutate({ listing_id: listingId })}>
        {selected ? "Unsave" : "Save property"}
      </button>
      {error && <p role="alert" className="text-red-700">{describeError(error)}</p>}
    </div>
  );
}

import { useEffect, useState } from "react";
import { api } from "../api";
import type { Receipt } from "../types";
import { Drawer, ZoneBadge, cap, timeAgo } from "./ui";

const REASONS: Record<string, string> = {
  one_time_used: "Used once, then deleted",
  expired: "Expired",
  user_deleted: "You deleted it",
  user_undo: "You pressed Undo",
  user_declined: "You said don't remember",
  user_command: "You asked to forget",
  zone_wiped: "Zone wiped",
  session_ended: "Chat ended",
};

export default function DeletionReceipts({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [receipts, setReceipts] = useState<Receipt[]>([]);
  useEffect(() => {
    if (open) api.receipts().then(setReceipts);
  }, [open]);

  return (
    <Drawer open={open} onClose={onClose} title="Deletion receipts" subtitle="Proof that things were deleted. Each receipt keeps only a fingerprint (hash), never the content.">
      {receipts.length === 0 ? (
        <p className="rounded-xl border border-dashed border-stone-200 px-4 py-8 text-center text-sm text-stone-500 dark:border-stone-700">Nothing has been deleted yet.</p>
      ) : (
        <ul className="space-y-2">
          {receipts.map((r) => (
            <li key={r.id} className="rounded-xl border border-stone-200 px-3.5 py-3 dark:border-stone-800">
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm font-medium text-stone-900 dark:text-stone-100">{REASONS[r.reason] ?? cap(r.reason)}</p>
                <span className="text-xs text-stone-400">{timeAgo(r.deleted_at)}</span>
              </div>
              <div className="mt-1.5 flex flex-wrap items-center gap-2">
                <ZoneBadge zone={r.zone} />
                <span className="text-xs text-stone-500">{cap(r.category)}</span>
                <code className="text-[11px] text-stone-400">sha256 {r.content_hash.slice(0, 16)}…</code>
              </div>
            </li>
          ))}
        </ul>
      )}
    </Drawer>
  );
}

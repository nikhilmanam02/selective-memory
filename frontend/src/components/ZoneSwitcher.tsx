import { EyeOff } from "lucide-react";
import type { Zone } from "../types";
import { ZONES, ZONE_META } from "./ui";

interface Props {
  zone: Zone;
  onChange: (zone: Zone) => void;
  hiddenCount: number;
}

export default function ZoneSwitcher({ zone, onChange, hiddenCount }: Props) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-2">
      <div role="tablist" aria-label="Memory zone" className="inline-flex max-w-full overflow-x-auto rounded-xl bg-stone-100 p-1 dark:bg-stone-800/60">
        {ZONES.map((item) => {
          const meta = ZONE_META[item];
          const Icon = meta.icon;
          const active = item === zone;
          return (
            <button
              key={item}
              role="tab"
              aria-selected={active}
              onClick={() => onChange(item)}
              className={`inline-flex shrink-0 items-center gap-1.5 rounded-lg px-2.5 py-1.5 sm:px-3 text-sm font-medium transition ${
                active ? meta.tab : "text-stone-500 hover:text-stone-800 dark:text-stone-400 dark:hover:text-stone-100"
              }`}
            >
              <Icon size={14} aria-hidden="true" />
              {meta.label}
            </button>
          );
        })}
      </div>
      {hiddenCount > 0 && (
        <p className="inline-flex items-center gap-1.5 text-xs text-stone-500 dark:text-stone-400" title="Memories from other zones are never sent to the AI while you're in this zone.">
          <EyeOff size={13} /> {hiddenCount} {hiddenCount === 1 ? "memory" : "memories"} hidden in this zone
        </p>
      )}
    </div>
  );
}

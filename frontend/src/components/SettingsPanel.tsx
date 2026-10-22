import { RotateCcw } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api";
import type { Preference } from "../types";
import { Drawer, ZONES, ZONE_META, buttonSecondary, cap } from "./ui";

interface Props {
  open: boolean;
  onClose: () => void;
}

const BEHAVIORS: { value: string; label: string; hint: string }[] = [
  { value: "auto_forever", label: "Save", hint: "Save quietly, usable everywhere" },
  { value: "zone_only", label: "Save to zone", hint: "Save quietly, only in one zone" },
  { value: "ask", label: "Ask me", hint: "Ask before saving" },
  { value: "never", label: "Never", hint: "Never save (unless I say “remember this”)" },
];

const DESCRIPTIONS: Record<string, string> = {
  preference: "Food, tastes, hobbies",
  identity: "Name, background",
  relationship: "Family and friends",
  schedule: "Plans and routines",
  location: "Where you are or live",
  work: "Job and colleagues",
  health: "Conditions, medication, appointments",
  finance: "Money, accounts, income",
  job_search: "Interviews, job hunting",
  other: "Anything else",
};

export default function SettingsPanel({ open, onClose }: Props) {
  const [preferences, setPreferences] = useState<Preference[]>([]);

  useEffect(() => {
    if (open) api.preferences().then(setPreferences);
  }, [open]);

  const update = async (item: Preference, behavior: string, zone?: string | null) => {
    const nextZone = behavior === "zone_only" ? zone ?? item.zone ?? "personal" : null;
    setPreferences(await api.setPreference(item.category, behavior, nextZone));
  };

  return (
    <Drawer open={open} onClose={onClose} title="How I handle your info" subtitle="Defaults for each kind of fact. I also learn from your answers: pick the same option 3 times and I stop asking.">
      <ul className="divide-y divide-stone-100 dark:divide-stone-800">
        {preferences
          .filter((item) => item.category !== "secret")
          .map((item) => (
            <li key={item.category} className="py-3">
              <div className="flex items-baseline justify-between gap-2">
                <div>
                  <p className="text-sm font-medium text-stone-900 dark:text-stone-100">
                    {cap(item.category)}
                    {item.source === "learned" && <span className="ml-2 rounded-full bg-indigo-50 px-1.5 py-0.5 text-[10px] font-medium text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-300">learned</span>}
                  </p>
                  <p className="text-xs text-stone-500">{DESCRIPTIONS[item.category]}</p>
                </div>
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-1.5">
                {BEHAVIORS.map((option) => {
                  const selected = item.behavior === option.value || (option.value === "zone_only" && item.behavior === "session");
                  return (
                    <button
                      key={option.value}
                      title={option.hint}
                      onClick={() => update(item, option.value)}
                      className={`rounded-lg px-2.5 py-1 text-xs font-medium transition ${
                        selected
                          ? "bg-stone-900 text-white dark:bg-white dark:text-stone-900"
                          : "bg-stone-100 text-stone-600 hover:bg-stone-200 dark:bg-stone-800 dark:text-stone-300 dark:hover:bg-stone-700"
                      }`}
                    >
                      {option.label}
                    </button>
                  );
                })}
                {item.behavior === "zone_only" && (
                  <select
                    value={item.zone ?? "personal"}
                    onChange={(e) => update(item, "zone_only", e.target.value)}
                    className="rounded-lg border border-stone-200 bg-white px-2 py-1 text-xs dark:border-stone-700 dark:bg-stone-900"
                    aria-label={`Zone for ${item.category}`}
                  >
                    {ZONES.map((z) => <option key={z} value={z}>{ZONE_META[z].label}</option>)}
                  </select>
                )}
              </div>
            </li>
          ))}
        <li className="py-3">
          <p className="text-sm font-medium text-stone-900 dark:text-stone-100">Secrets</p>
          <p className="text-xs text-stone-500">Card numbers, passwords, codes, ID numbers: always used once and deleted. This can't be changed.</p>
        </li>
      </ul>
      <button
        className={`${buttonSecondary} mt-4`}
        onClick={async () => {
          await api.resetPreferences();
          setPreferences(await api.preferences());
        }}
      >
        <RotateCcw size={14} /> Reset what I've learned
      </button>
    </Drawer>
  );
}

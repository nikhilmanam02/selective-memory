import { Briefcase, Globe, HeartPulse, User, Wallet, X, type LucideIcon } from "lucide-react";
import { useEffect, type ReactNode } from "react";

export const ZONES = ["personal", "work", "health", "finance"] as const;

export const ZONE_META: Record<string, { label: string; icon: LucideIcon; badge: string; tab: string; dot: string }> = {
  global: {
    label: "Everywhere",
    icon: Globe,
    badge: "bg-white text-stone-700 ring-stone-300 dark:bg-stone-900 dark:text-stone-300 dark:ring-stone-700",
    tab: "",
    dot: "bg-stone-500",
  },
  personal: {
    label: "Personal",
    icon: User,
    badge: "bg-indigo-50 text-indigo-700 ring-indigo-200 dark:bg-indigo-500/10 dark:text-indigo-300 dark:ring-indigo-500/30",
    tab: "bg-white text-indigo-700 shadow-sm dark:bg-stone-800 dark:text-indigo-300",
    dot: "bg-indigo-500",
  },
  work: {
    label: "Work",
    icon: Briefcase,
    badge: "bg-sky-50 text-sky-700 ring-sky-200 dark:bg-sky-500/10 dark:text-sky-300 dark:ring-sky-500/30",
    tab: "bg-white text-sky-700 shadow-sm dark:bg-stone-800 dark:text-sky-300",
    dot: "bg-sky-500",
  },
  health: {
    label: "Health",
    icon: HeartPulse,
    badge: "bg-rose-50 text-rose-700 ring-rose-200 dark:bg-rose-500/10 dark:text-rose-300 dark:ring-rose-500/30",
    tab: "bg-white text-rose-700 shadow-sm dark:bg-stone-800 dark:text-rose-300",
    dot: "bg-rose-500",
  },
  finance: {
    label: "Finance",
    icon: Wallet,
    badge: "bg-amber-50 text-amber-800 ring-amber-200 dark:bg-amber-500/10 dark:text-amber-300 dark:ring-amber-500/30",
    tab: "bg-white text-amber-800 shadow-sm dark:bg-stone-800 dark:text-amber-300",
    dot: "bg-amber-500",
  },
};

export const RULE_META: Record<string, { label: string; badge: string }> = {
  forever: { label: "Forever", badge: "bg-stone-100 text-stone-600 ring-stone-200 dark:bg-stone-800 dark:text-stone-300 dark:ring-stone-700" },
  temporary: { label: "Temporary", badge: "bg-stone-100 text-stone-600 ring-stone-200 dark:bg-stone-800 dark:text-stone-300 dark:ring-stone-700" },
  zone_only: { label: "Zone only", badge: "bg-stone-100 text-stone-600 ring-stone-200 dark:bg-stone-800 dark:text-stone-300 dark:ring-stone-700" },
  session: { label: "This chat", badge: "bg-teal-50 text-teal-700 ring-teal-200 dark:bg-teal-500/10 dark:text-teal-300 dark:ring-teal-500/30" },
  one_time: { label: "Use once", badge: "bg-red-50 text-red-700 ring-red-200 dark:bg-red-500/10 dark:text-red-300 dark:ring-red-500/30" },
};

export function cap(text: string) {
  return text ? text[0].toUpperCase() + text.slice(1).replace(/_/g, " ") : text;
}

export function Badge({ className, children, title }: { className: string; children: ReactNode; title?: string }) {
  return (
    <span title={title} className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 ring-inset ${className}`}>
      {children}
    </span>
  );
}

export function ZoneBadge({ zone }: { zone: string }) {
  const meta = ZONE_META[zone] ?? ZONE_META.personal;
  const Icon = meta.icon;
  return (
    <Badge className={meta.badge}>
      <Icon size={11} aria-hidden="true" />
      {meta.label}
    </Badge>
  );
}

export function RuleBadge({ rule }: { rule: string }) {
  const meta = RULE_META[rule] ?? RULE_META.forever;
  return <Badge className={meta.badge}>{meta.label}</Badge>;
}

export function timeAgo(iso: string | null) {
  if (!iso) return "never";
  const seconds = Math.max(0, (Date.now() - Date.parse(iso)) / 1000);
  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

export function timeLeft(iso: string | null) {
  if (!iso) return "";
  const ms = Date.parse(iso) - Date.now();
  if (ms <= 0) return "expiring";
  const hours = ms / 3_600_000;
  if (hours < 1) return `${Math.ceil(ms / 60_000)}m left`;
  if (hours < 48) return `${Math.round(hours)}h left`;
  return `until ${new Date(iso).toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" })}`;
}

export const buttonPrimary =
  "inline-flex items-center justify-center gap-1.5 rounded-xl bg-indigo-600 px-3.5 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50";
export const buttonSecondary =
  "inline-flex items-center justify-center gap-1.5 rounded-xl border border-stone-200 bg-white px-3.5 py-2 text-sm font-medium text-stone-700 transition hover:bg-stone-50 disabled:opacity-50 dark:border-stone-700 dark:bg-stone-900 dark:text-stone-200 dark:hover:bg-stone-800";
export const buttonGhost =
  "inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium text-stone-500 transition hover:bg-stone-100 hover:text-stone-800 dark:text-stone-400 dark:hover:bg-stone-800 dark:hover:text-stone-100";
export const inputClass =
  "w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-900 outline-none transition placeholder:text-stone-400 focus:border-indigo-400 focus:ring-4 focus:ring-indigo-100 dark:border-stone-700 dark:bg-stone-900 dark:text-stone-100 dark:focus:ring-indigo-500/20";

function useEscape(open: boolean, onClose: () => void) {
  useEffect(() => {
    if (!open) return;
    const handler = (event: KeyboardEvent) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, onClose]);
}

export function Drawer({
  open,
  onClose,
  title,
  subtitle,
  children,
  width = "max-w-lg",
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  children: ReactNode;
  width?: string;
}) {
  useEscape(open, onClose);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-stone-950/30 backdrop-blur-[2px] animate-fade-in" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <aside role="dialog" aria-modal="true" aria-label={title} className={`flex h-full w-full ${width} flex-col bg-white shadow-2xl animate-slide-left dark:bg-stone-900`}>
        <header className="flex items-start justify-between gap-4 border-b border-stone-100 px-6 py-5 dark:border-stone-800">
          <div>
            <h2 className="text-base font-semibold tracking-tight text-stone-900 dark:text-stone-50">{title}</h2>
            {subtitle && <p className="mt-0.5 text-sm text-stone-500 dark:text-stone-400">{subtitle}</p>}
          </div>
          <button onClick={onClose} className="rounded-lg p-1.5 text-stone-400 hover:bg-stone-100 hover:text-stone-700 dark:hover:bg-stone-800" aria-label="Close">
            <X size={18} />
          </button>
        </header>
        <div className="min-h-0 flex-1 overflow-y-auto px-6 py-5">{children}</div>
      </aside>
    </div>
  );
}

export function Modal({ open, onClose, title, children }: { open: boolean; onClose: () => void; title: string; children: ReactNode }) {
  useEscape(open, onClose);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-stone-950/40 p-4 backdrop-blur-[2px] animate-fade-in" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div role="dialog" aria-modal="true" aria-label={title} className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl animate-pop dark:bg-stone-900">
        <div className="flex items-start justify-between gap-4">
          <h2 className="text-base font-semibold tracking-tight text-stone-900 dark:text-stone-50">{title}</h2>
          <button onClick={onClose} className="-m-1 rounded-lg p-1.5 text-stone-400 hover:bg-stone-100 hover:text-stone-700 dark:hover:bg-stone-800" aria-label="Close">
            <X size={18} />
          </button>
        </div>
        <div className="mt-4">{children}</div>
      </div>
    </div>
  );
}

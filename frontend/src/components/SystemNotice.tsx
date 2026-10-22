import type { ReactNode } from "react";

export default function SystemNotice({ children, tone = "neutral" }: { children: ReactNode; tone?: "neutral" | "error" }) {
  return (
    <div className="my-3 flex justify-center">
      <p
        className={`max-w-[90%] rounded-full px-3 py-1 text-center text-xs ${
          tone === "error"
            ? "bg-red-50 text-red-700 dark:bg-red-500/10 dark:text-red-300"
            : "text-stone-500 dark:text-stone-400"
        }`}
      >
        {children}
      </p>
    </div>
  );
}

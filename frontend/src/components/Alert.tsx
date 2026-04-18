import type { ReactNode } from "react";

export function AlertError({ children }: { children: ReactNode }) {
  return (
    <div
      role="alert"
      className="rounded-2xl border border-red-200/80 bg-gradient-to-br from-red-50 to-red-50/50 px-5 py-4 text-sm text-red-900 shadow-sm"
    >
      {children}
    </div>
  );
}

export function AlertSuccess({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-2xl border border-emerald-200/80 bg-gradient-to-br from-emerald-50 to-teal-50/40 px-5 py-4 text-sm text-emerald-900 shadow-sm">
      {children}
    </div>
  );
}

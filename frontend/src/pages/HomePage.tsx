import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiJson } from "../api";
import { AlertError } from "../components/Alert";
import { PageLoader } from "../components/PageLoader";
import type { Property } from "../types";

const statusLabel: Record<string, string> = {
  free: "Свободен",
  listed_ykt: "Выложен в YKT",
  occupied: "Занят",
};

const statusStyle: Record<string, string> = {
  free: "bg-emerald-50 text-emerald-800 ring-emerald-500/20",
  listed_ykt: "bg-amber-50 text-amber-900 ring-amber-500/20",
  occupied: "bg-brand-50 text-brand-800 ring-brand-500/25",
};

export function HomePage() {
  const [items, setItems] = useState<Property[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiJson<Property[]>("/api/properties")
      .then(setItems)
      .catch((e: Error) => setErr(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <PageLoader />;
  }

  return (
    <div className="animate-fade-in space-y-10">
      <section className="relative overflow-hidden rounded-3xl border border-white/60 bg-gradient-to-br from-white via-white to-brand-50/40 p-8 sm:p-10 shadow-lift">
        <div className="pointer-events-none absolute -right-16 -top-16 h-48 w-48 rounded-full bg-brand-400/15 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-8 left-1/3 h-32 w-32 rounded-full bg-amber-300/10 blur-2xl" />
        <div className="relative max-w-2xl">
          <p className="text-xs font-bold uppercase tracking-[0.25em] text-brand-600">Объекты</p>
          <h1 className="mt-2 font-display text-3xl font-bold tracking-tight text-ink-900 sm:text-4xl">
            Вся аренда в одном месте
          </h1>
          <p className="mt-3 text-base leading-relaxed text-ink-600">
            Карточки недвижимости, сроки аренды и напоминания о платежах — без таблиц и хаоса в почте.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/properties/new" className="btn-primary">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" className="opacity-90">
                <path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
              Новый объект
            </Link>
          </div>
        </div>
      </section>

      {err && <AlertError>{err}</AlertError>}

      {items.length === 0 ? (
        <div className="card-elevated flex flex-col items-center justify-center px-8 py-16 text-center">
          <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-surface-muted text-brand-600">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M4 20V10l8-6 8 6v10M9 20v-6h6v6" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <h2 className="font-display text-xl font-semibold text-ink-900">Пока пусто</h2>
          <p className="mt-2 max-w-sm text-sm text-ink-500">
            Создайте первый объект — дальше можно добавить арендатора и даты.
          </p>
          <Link to="/properties/new" className="btn-primary mt-6">
            Добавить объект
          </Link>
        </div>
      ) : (
        <ul className="grid gap-5 sm:grid-cols-2">
          {items.map((p) => (
            <li key={p.id} className="animate-fade-in">
              <Link
                to={`/properties/${p.id}`}
                className="group card-elevated block overflow-hidden p-6 transition-all duration-300 hover:border-brand-400/25 hover:shadow-glow"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <h2 className="font-display text-lg font-semibold text-ink-900 transition group-hover:text-brand-700">
                      {p.name}
                    </h2>
                    <p className="mt-2 line-clamp-2 text-sm leading-relaxed text-ink-500">{p.address}</p>
                  </div>
                  <span
                    className={`badge shrink-0 ring-1 ${statusStyle[p.status] ?? "bg-ink-100 text-ink-700 ring-ink-900/10"}`}
                  >
                    {statusLabel[p.status] ?? p.status}
                  </span>
                </div>
                <div className="mt-5 flex items-center gap-2 border-t border-ink-900/[0.06] pt-4 text-xs text-ink-500">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" className="shrink-0 text-brand-500">
                    <path
                      d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"
                      stroke="currentColor"
                      strokeWidth="1.5"
                    />
                    <path d="M22 6l-10 7L2 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                  </svg>
                  <span className="truncate font-medium text-ink-600">{p.owner_email}</span>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

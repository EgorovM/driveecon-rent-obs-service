import { FormEvent, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiJson } from "../api";
import { AlertError, AlertSuccess } from "../components/Alert";
import { PageLoader } from "../components/PageLoader";
import type { ConfirmInfo } from "../types";

export function ConfirmPage() {
  const { token } = useParams();
  const [info, setInfo] = useState<ConfirmInfo | null>(null);
  const [text, setText] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    apiJson<ConfirmInfo>(`/api/confirm/${token}`)
      .then(setInfo)
      .catch((e: Error) => setErr(e.message))
      .finally(() => setLoading(false));
  }, [token]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!token) return;
    setErr(null);
    setOk(null);
    try {
      const r = await apiJson<{ detail: string }>(`/api/confirm/${token}`, {
        method: "POST",
        body: JSON.stringify({ confirmation_text: text }),
      });
      setOk(r.detail);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Ошибка");
    }
  }

  if (loading) {
    return <PageLoader label="Открываем данные аренды…" />;
  }

  if (err && !info) {
    return (
      <div className="mx-auto max-w-md animate-fade-in">
        <AlertError>{err}</AlertError>
        <Link to="/" className="mt-6 inline-flex text-sm font-medium text-brand-700 hover:text-brand-600">
          ← На главную
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-lg animate-fade-in">
      <div className="mb-8 text-center">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-400 to-brand-600 shadow-lg shadow-brand-600/25">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" className="text-white">
            <path
              d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>
        <h1 className="font-display text-2xl font-bold tracking-tight text-ink-900 sm:text-3xl">
          Подтверждение оплаты
        </h1>
        <p className="mt-2 text-sm text-ink-600">
          Кратко опишите, что аренду оплатили — владелец получит уведомление.
        </p>
      </div>

      {info && (
        <div className="card-elevated mb-8 overflow-hidden">
          <div className="bg-gradient-to-r from-brand-50/90 to-transparent px-6 py-4">
            <p className="text-xs font-bold uppercase tracking-wider text-brand-700">Объект</p>
            <p className="mt-1 font-display text-lg font-semibold text-ink-900">{info.property_name}</p>
          </div>
          <div className="space-y-3 px-6 py-5 text-sm">
            <p className="flex gap-2 text-ink-600">
              <span className="shrink-0 text-ink-400">Адрес</span>
              <span className="font-medium text-ink-800">{info.address}</span>
            </p>
            <p className="flex gap-2 text-ink-600">
              <span className="shrink-0 text-ink-400">Арендатор</span>
              <span className="font-medium text-ink-800">{info.tenant_name}</span>
            </p>
            <p className="flex gap-2 text-ink-600">
              <span className="shrink-0 text-ink-400">До</span>
              <span className="font-medium text-ink-800">{info.rent_end}</span>
            </p>
          </div>
        </div>
      )}

      {ok ? (
        <AlertSuccess>
          <span className="flex items-start gap-3">
            <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-emerald-500 text-white">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                <path d="M20 6L9 17l-5-5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </span>
            <span>{ok}</span>
          </span>
        </AlertSuccess>
      ) : (
        <form onSubmit={onSubmit} className="card-elevated space-y-5 p-6 sm:p-8">
          <div>
            <label className="label">Текст подтверждения</label>
            <textarea
              className="input-field min-h-[120px] resize-y"
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Например: подтверждаю оплату аренды за текущий период переводом на карту"
              required
            />
            <p className="mt-2 text-xs text-ink-500">
              Упомяните оплату или перевод — так проще проверить корректность.
            </p>
          </div>
          {err && <AlertError>{err}</AlertError>}
          <button type="submit" className="btn-primary w-full justify-center py-3">
            Отправить подтверждение
          </button>
        </form>
      )}

      <div className="mt-10 text-center">
        <Link to="/" className="text-sm font-medium text-brand-700 transition hover:text-brand-600">
          На главную
        </Link>
      </div>
    </div>
  );
}

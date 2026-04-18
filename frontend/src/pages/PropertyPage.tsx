import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { apiJson, apiUpload } from "../api";
import { AlertError, AlertSuccess } from "../components/Alert";
import { PageLoader } from "../components/PageLoader";
import type { Lease, Property, PropertyStatus } from "../types";

const statuses: { value: PropertyStatus; label: string }[] = [
  { value: "free", label: "Свободен" },
  { value: "listed_ykt", label: "Выложен в YKT" },
  { value: "occupied", label: "Занят" },
];

const payLabel: Record<string, string> = {
  pending: "Ожидает оплаты",
  paid: "Оплачено",
  overdue: "Просрочено",
};

const payStyle: Record<string, string> = {
  pending: "bg-amber-50 text-amber-900 ring-amber-500/20",
  paid: "bg-emerald-50 text-emerald-800 ring-emerald-500/20",
  overdue: "bg-red-50 text-red-800 ring-red-500/20",
};

export function PropertyPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const isNew = !id;

  const [name, setName] = useState("");
  const [address, setAddress] = useState("");
  const [status, setStatus] = useState<PropertyStatus>("free");
  const [ownerEmail, setOwnerEmail] = useState("");
  const [leases, setLeases] = useState<Lease[]>([]);

  const [tenantName, setTenantName] = useState("");
  const [tenantEmail, setTenantEmail] = useState("");
  const [rentStart, setRentStart] = useState("");
  const [rentEnd, setRentEnd] = useState("");
  const [file, setFile] = useState<File | null>(null);

  const [err, setErr] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [loading, setLoading] = useState(!isNew);

  const [testLeaseId, setTestLeaseId] = useState("");
  const [testToEmail, setTestToEmail] = useState("");
  const [testOwnerEmail, setTestOwnerEmail] = useState("");
  const [testSending, setTestSending] = useState(false);
  const [leaseEmailDrafts, setLeaseEmailDrafts] = useState<Record<string, string>>({});
  const [savingLeaseId, setSavingLeaseId] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    apiJson<Property>(`/api/properties/${id}`)
      .then((p) => {
        setName(p.name);
        setAddress(p.address);
        setStatus(p.status);
        setOwnerEmail(p.owner_email);
      })
      .catch((e: Error) => setErr(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    if (!id) return;
    apiJson<Lease[]>(`/api/properties/${id}/leases`)
      .then(setLeases)
      .catch(() => {});
  }, [id]);

  useEffect(() => {
    if (leases.length === 0) return;
    setTestLeaseId((prev) => prev || leases[0].id);
    setTestToEmail((prev) => prev || leases[0].tenant_email);
  }, [leases]);

  useEffect(() => {
    if (ownerEmail) setTestOwnerEmail(ownerEmail);
  }, [ownerEmail]);

  useEffect(() => {
    const m: Record<string, string> = {};
    leases.forEach((l) => {
      m[l.id] = l.tenant_email;
    });
    setLeaseEmailDrafts(m);
  }, [leases]);

  async function saveProperty(e: FormEvent) {
    e.preventDefault();
    setErr(null);
    setMsg(null);
    try {
      if (isNew) {
        const p = await apiJson<Property>("/api/properties", {
          method: "POST",
          body: JSON.stringify({
            name,
            address,
            status,
            owner_email: ownerEmail,
          }),
        });
        navigate(`/properties/${p.id}`, { replace: true });
      } else {
        await apiJson(`/api/properties/${id}`, {
          method: "PATCH",
          body: JSON.stringify({
            name,
            address,
            status,
            owner_email: ownerEmail,
          }),
        });
        setMsg("Изменения сохранены");
      }
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Ошибка");
    }
  }

  async function addLease(e: FormEvent) {
    e.preventDefault();
    if (!id) return;
    setErr(null);
    setMsg(null);
    try {
      if (file) {
        await apiUpload<Lease>(`/api/properties/${id}/leases/upload`, file);
        setFile(null);
      } else {
        if (!tenantName.trim() || !tenantEmail.trim() || !rentStart || !rentEnd) {
          setErr("Заполните ФИО, email и даты или загрузите .txt");
          return;
        }
        await apiJson<Lease>(`/api/properties/${id}/leases`, {
          method: "POST",
          body: JSON.stringify({
            tenant_name: tenantName,
            tenant_email: tenantEmail,
            rent_start: rentStart,
            rent_end: rentEnd,
          }),
        });
        setTenantName("");
        setTenantEmail("");
        setRentStart("");
        setRentEnd("");
      }
      const list = await apiJson<Lease[]>(`/api/properties/${id}/leases`);
      setLeases(list);
      setMsg("Аренда добавлена");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Ошибка");
    }
  }

  async function sendTestTenantReminder() {
    if (!testLeaseId) {
      setErr("Выберите аренду для теста");
      return;
    }
    setErr(null);
    setMsg(null);
    setTestSending(true);
    try {
      const body: { lease_id: string; to_email?: string } = { lease_id: testLeaseId };
      if (testToEmail.trim()) body.to_email = testToEmail.trim();
      await apiJson<{ detail: string }>("/api/email/test/tenant-reminder", {
        method: "POST",
        body: JSON.stringify(body),
      });
      setMsg("Тестовое письмо «надо заплатить» отправлено на указанный email.");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Ошибка отправки");
    } finally {
      setTestSending(false);
    }
  }

  async function sendTestOwnerPaid() {
    if (!testLeaseId) {
      setErr("Выберите аренду для теста");
      return;
    }
    if (!testOwnerEmail.trim()) {
      setErr("Укажите email владельца");
      return;
    }
    setErr(null);
    setMsg(null);
    setTestSending(true);
    try {
      await apiJson<{ detail: string }>("/api/email/test/owner-paid", {
        method: "POST",
        body: JSON.stringify({
          lease_id: testLeaseId,
          to_email: testOwnerEmail,
        }),
      });
      setMsg("Тест: письмо владельцу «оплата подтверждена» отправлено.");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Ошибка отправки");
    } finally {
      setTestSending(false);
    }
  }

  async function saveLeaseTenantEmail(leaseId: string) {
    if (!id) return;
    const email = leaseEmailDrafts[leaseId]?.trim();
    if (!email) {
      setErr("Укажите email арендатора");
      return;
    }
    setErr(null);
    setMsg(null);
    setSavingLeaseId(leaseId);
    try {
      await apiJson(`/api/properties/${id}/leases/${leaseId}`, {
        method: "PATCH",
        body: JSON.stringify({ tenant_email: email }),
      });
      const list = await apiJson<Lease[]>(`/api/properties/${id}/leases`);
      setLeases(list);
      if (testLeaseId === leaseId) setTestToEmail(email);
      setMsg("Email арендатора сохранён — напоминания пойдут на этот адрес.");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Ошибка");
    } finally {
      setSavingLeaseId(null);
    }
  }

  async function sendTestOwnerNotPaid() {
    if (!testLeaseId) {
      setErr("Выберите аренду для теста");
      return;
    }
    if (!testOwnerEmail.trim()) {
      setErr("Укажите email владельца");
      return;
    }
    setErr(null);
    setMsg(null);
    setTestSending(true);
    try {
      await apiJson<{ detail: string }>("/api/email/test/owner-not-paid", {
        method: "POST",
        body: JSON.stringify({
          lease_id: testLeaseId,
          to_email: testOwnerEmail,
        }),
      });
      setMsg("Тест: письмо владельцу «нет подтверждения оплаты» отправлено.");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Ошибка отправки");
    } finally {
      setTestSending(false);
    }
  }

  if (loading) {
    return <PageLoader label="Загружаем объект…" />;
  }

  return (
    <div className="mx-auto max-w-3xl animate-fade-in space-y-10">
      <div>
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-sm font-medium text-brand-700 transition hover:text-brand-600"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M15 18l-6-6 6-6" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          К списку объектов
        </Link>
        <h1 className="mt-4 font-display text-3xl font-bold tracking-tight text-ink-900">
          {isNew ? "Новый объект" : "Карточка объекта"}
        </h1>
        <p className="mt-2 text-ink-600">
          {isNew ? "Заполните основные данные — потом можно добавить аренду." : "Редактируйте данные и управляйте арендой."}
        </p>
      </div>

      {err && <AlertError>{err}</AlertError>}
      {msg && <AlertSuccess>{msg}</AlertSuccess>}

      <section className="card-elevated p-6 sm:p-8">
        <div className="mb-6 flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <path d="M4 20V10l8-6 8 6v10M9 20v-6h6v6" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </span>
          <div>
            <h2 className="font-display text-lg font-semibold text-ink-900">Основное</h2>
            <p className="text-xs text-ink-500">Название, адрес, статус, контакт владельца</p>
          </div>
        </div>

        <form onSubmit={saveProperty} className="space-y-5">
          <div>
            <label className="label">Название</label>
            <input
              className="input-field"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Например: 2-комн. на Ленина"
              required
            />
          </div>
          <div>
            <label className="label">Адрес</label>
            <textarea
              className="input-field min-h-[100px] resize-y"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              placeholder="Полный адрес для писем и напоминаний"
              required
            />
          </div>
          <div className="grid gap-5 sm:grid-cols-2">
            <div>
              <label className="label">Статус</label>
              <select
                className="input-field cursor-pointer appearance-none bg-[length:1rem] bg-[right_0.75rem_center] bg-no-repeat pr-10"
                style={{
                  backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%236b7280'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'/%3E%3C/svg%3E")`,
                }}
                value={status}
                onChange={(e) => setStatus(e.target.value as PropertyStatus)}
              >
                {statuses.map((s) => (
                  <option key={s.value} value={s.value}>
                    {s.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">Email владельца</label>
              <input
                type="email"
                className="input-field"
                value={ownerEmail}
                onChange={(e) => setOwnerEmail(e.target.value)}
                placeholder="owner@example.com"
                required
              />
            </div>
          </div>
          <button type="submit" className="btn-dark">
            {isNew ? "Создать объект" : "Сохранить изменения"}
          </button>
        </form>
      </section>

      {!isNew && (
        <>
          <section className="card-elevated overflow-hidden">
            <div className="border-b border-ink-900/[0.06] bg-gradient-to-r from-brand-50/80 to-transparent px-6 py-5 sm:px-8">
              <h2 className="font-display text-lg font-semibold text-ink-900">Занять объект</h2>
              <p className="mt-1 text-sm text-ink-600">
                Вручную или загрузите .txt с ФИО, email и датами начала и окончания аренды.
              </p>
            </div>
            <form onSubmit={addLease} className="space-y-5 p-6 sm:p-8">
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="label">ФИО арендатора</label>
                  <input
                    className="input-field"
                    value={tenantName}
                    onChange={(e) => setTenantName(e.target.value)}
                    placeholder="Иванов Иван"
                  />
                </div>
                <div>
                  <label className="label">Email арендатора</label>
                  <input
                    type="email"
                    className="input-field"
                    value={tenantEmail}
                    onChange={(e) => setTenantEmail(e.target.value)}
                    placeholder="tenant@mail.ru"
                  />
                </div>
                <div>
                  <label className="label">Начало аренды</label>
                  <input
                    type="date"
                    className="input-field"
                    value={rentStart}
                    onChange={(e) => setRentStart(e.target.value)}
                  />
                </div>
                <div>
                  <label className="label">Окончание аренды</label>
                  <input
                    type="date"
                    className="input-field"
                    value={rentEnd}
                    onChange={(e) => setRentEnd(e.target.value)}
                  />
                </div>
              </div>

              <div className="rounded-2xl border-2 border-dashed border-brand-300/50 bg-brand-50/30 px-5 py-6 text-center transition hover:border-brand-400/60 hover:bg-brand-50/50">
                <label className="label mb-2">Или файл .txt</label>
                <input
                  type="file"
                  accept=".txt,text/plain"
                  className="mx-auto block w-full max-w-sm cursor-pointer text-sm text-ink-600 file:mr-4 file:cursor-pointer file:rounded-lg file:border-0 file:bg-brand-500 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-white hover:file:bg-brand-600"
                  onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                />
                {file && (
                  <p className="mt-3 text-xs font-medium text-brand-700">Выбран: {file.name}</p>
                )}
              </div>

              <button type="submit" className="btn-primary w-full justify-center py-3">
                Добавить аренду
              </button>
            </form>
          </section>

          {leases.length > 0 && (
            <section>
              <h3 className="mb-4 font-display text-base font-semibold text-ink-900">История аренды</h3>
              <ul className="space-y-3">
                {leases.map((l) => (
                  <li key={l.id} className="card-elevated flex flex-col gap-4 p-5">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                      <div>
                        <p className="font-medium text-ink-900">{l.tenant_name}</p>
                        <p className="text-xs text-ink-500 mt-1">
                          На этот email уходят напоминания арендатору (в т.ч. из планировщика).
                        </p>
                      </div>
                      <div className="flex flex-wrap items-center gap-3 text-sm">
                        <span className="inline-flex items-center gap-1.5 rounded-lg bg-surface-muted px-2.5 py-1 text-ink-600">
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" className="text-brand-500">
                            <rect x="3" y="4" width="18" height="18" rx="2" stroke="currentColor" strokeWidth="1.5" />
                            <path d="M16 2v4M8 2v4M3 10h18" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                          </svg>
                          {l.rent_start} — {l.rent_end}
                        </span>
                        <span
                          className={`badge ring-1 ${payStyle[l.payment_status] ?? "bg-ink-100 text-ink-700"}`}
                        >
                          {payLabel[l.payment_status] ?? l.payment_status}
                        </span>
                      </div>
                    </div>
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
                      <div className="flex-1 min-w-0">
                        <label className="label text-xs">Email арендатора</label>
                        <input
                          type="email"
                          className="input-field"
                          value={leaseEmailDrafts[l.id] ?? l.tenant_email}
                          onChange={(e) =>
                            setLeaseEmailDrafts((prev) => ({ ...prev, [l.id]: e.target.value }))
                          }
                        />
                      </div>
                      <button
                        type="button"
                        disabled={savingLeaseId === l.id}
                        onClick={() => void saveLeaseTenantEmail(l.id)}
                        className="btn-secondary shrink-0 py-2.5 sm:mb-0.5"
                      >
                        {savingLeaseId === l.id ? "Сохранение…" : "Сохранить email"}
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {leases.length > 0 && (
            <section className="rounded-2xl border border-amber-200/80 bg-gradient-to-br from-amber-50/90 to-orange-50/40 p-6 sm:p-8">
              <h3 className="font-display text-base font-semibold text-amber-950">Тестовая отправка почты</h3>
              <p className="mt-1 text-sm text-amber-900/80">
                Те же шаблоны, что в проде: напоминание арендатору; владельцу — при подтверждении оплаты или при
                отсутствии оплаты (как после дедлайна).
              </p>
              <div className="mt-5 space-y-6">
                <div>
                  <label className="label text-amber-900/70">Аренда (контекст письма)</label>
                  <select
                    className="input-field"
                    value={testLeaseId}
                    onChange={(e) => {
                      const lid = e.target.value;
                      setTestLeaseId(lid);
                      const l = leases.find((x) => x.id === lid);
                      if (l) setTestToEmail(l.tenant_email);
                    }}
                  >
                    {leases.map((l) => (
                      <option key={l.id} value={l.id}>
                        {l.tenant_name} · до {l.rent_end}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="rounded-xl border border-amber-200/60 bg-white/60 p-4 space-y-4">
                  <p className="text-xs font-semibold uppercase tracking-wider text-amber-900/70">Арендатору</p>
                  <div>
                    <label className="label text-amber-900/70">Куда отправить</label>
                    <input
                      type="email"
                      className="input-field"
                      value={testToEmail}
                      onChange={(e) => setTestToEmail(e.target.value)}
                      placeholder="email арендатора"
                    />
                  </div>
                  <button
                    type="button"
                    disabled={testSending}
                    onClick={() => void sendTestTenantReminder()}
                    className="btn-primary w-full justify-center py-3 disabled:opacity-60"
                  >
                    {testSending ? "Отправка…" : "Напоминание об оплате (тест)"}
                  </button>
                </div>

                <div className="rounded-xl border border-amber-200/60 bg-white/60 p-4 space-y-4">
                  <p className="text-xs font-semibold uppercase tracking-wider text-amber-900/70">Владельцу</p>
                  <div>
                    <label className="label text-amber-900/70">Куда отправить</label>
                    <input
                      type="email"
                      className="input-field"
                      value={testOwnerEmail}
                      onChange={(e) => setTestOwnerEmail(e.target.value)}
                      placeholder="email владельца из карточки"
                    />
                  </div>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <button
                      type="button"
                      disabled={testSending}
                      onClick={() => void sendTestOwnerPaid()}
                      className="rounded-xl border border-emerald-200 bg-gradient-to-br from-emerald-50 to-teal-50/80 px-4 py-3 text-sm font-semibold text-emerald-900 shadow-sm transition hover:border-emerald-300 disabled:opacity-60"
                    >
                      {testSending ? "…" : "Оплата подтверждена (тест)"}
                    </button>
                    <button
                      type="button"
                      disabled={testSending}
                      onClick={() => void sendTestOwnerNotPaid()}
                      className="rounded-xl border border-rose-200 bg-gradient-to-br from-rose-50 to-orange-50/50 px-4 py-3 text-sm font-semibold text-rose-900 shadow-sm transition hover:border-rose-300 disabled:opacity-60"
                    >
                      {testSending ? "…" : "Нет оплаты (тест)"}
                    </button>
                  </div>
                  <p className="text-xs text-amber-900/70 leading-relaxed">
                    «Оплата подтверждена» — как после ссылки подтверждения арендатором. «Нет оплаты» — как при
                    просрочке без оплаты.
                  </p>
                </div>
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}

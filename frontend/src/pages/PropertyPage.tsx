import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { apiJson, apiUpload } from "../api";
import { AlertError, AlertSuccess } from "../components/Alert";
import { PageLoader } from "../components/PageLoader";
import type { Lease, Property, PropertyStatus, RentPeriod } from "../types";

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

const MONTHS = [
  "", "январь", "февраль", "март", "апрель", "май", "июнь",
  "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь",
];

const money = (n: number) => `${n.toLocaleString("ru-RU")} ₽`;
const monthLabel = (y: number, m: number) => `${MONTHS[m] ?? m} ${y}`;

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
  const [rentAmount, setRentAmount] = useState("");
  const [paymentDay, setPaymentDay] = useState("");
  const [contractNumber, setContractNumber] = useState("");
  const [contractDate, setContractDate] = useState("");
  const [file, setFile] = useState<File | null>(null);

  const [err, setErr] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [loading, setLoading] = useState(!isNew);

  const [payDrafts, setPayDrafts] = useState<Record<string, string>>({});
  const [busyPeriodId, setBusyPeriodId] = useState<string | null>(null);

  const [testPeriodId, setTestPeriodId] = useState("");
  const [testToEmail, setTestToEmail] = useState("");
  const [testOwnerEmail, setTestOwnerEmail] = useState("");
  const [testSending, setTestSending] = useState(false);

  const allPeriods: { lease: Lease; period: RentPeriod }[] = leases.flatMap((l) =>
    l.periods.map((p) => ({ lease: l, period: p })),
  );

  async function reloadLeases() {
    if (!id) return;
    const list = await apiJson<Lease[]>(`/api/properties/${id}/leases`);
    setLeases(list);
  }

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
    if (ownerEmail) setTestOwnerEmail((prev) => prev || ownerEmail);
  }, [ownerEmail]);

  useEffect(() => {
    if (allPeriods.length === 0) return;
    setTestPeriodId((prev) => prev || allPeriods[0].period.id);
    setTestToEmail((prev) => prev || allPeriods[0].lease.tenant_email);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [leases]);

  async function saveProperty(e: FormEvent) {
    e.preventDefault();
    setErr(null);
    setMsg(null);
    try {
      if (isNew) {
        const p = await apiJson<Property>("/api/properties", {
          method: "POST",
          body: JSON.stringify({ name, address, status, owner_email: ownerEmail }),
        });
        navigate(`/properties/${p.id}`, { replace: true });
      } else {
        await apiJson(`/api/properties/${id}`, {
          method: "PATCH",
          body: JSON.stringify({ name, address, status, owner_email: ownerEmail }),
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
        if (!tenantName.trim() || !tenantEmail.trim() || !rentStart || !rentEnd || !rentAmount || !paymentDay) {
          setErr("Заполните ФИО, email, даты, сумму и день оплаты — или загрузите .txt");
          return;
        }
        await apiJson<Lease>(`/api/properties/${id}/leases`, {
          method: "POST",
          body: JSON.stringify({
            tenant_name: tenantName,
            tenant_email: tenantEmail,
            rent_start: rentStart,
            rent_end: rentEnd,
            rent_amount: Number(rentAmount),
            payment_day: Number(paymentDay),
            contract_number: contractNumber.trim() || null,
            contract_date: contractDate || null,
          }),
        });
        setTenantName("");
        setTenantEmail("");
        setRentStart("");
        setRentEnd("");
        setRentAmount("");
        setPaymentDay("");
        setContractNumber("");
        setContractDate("");
      }
      await reloadLeases();
      setMsg("Аренда добавлена — начисления по месяцам созданы");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Ошибка");
    }
  }

  async function recordPayment(lease: Lease, period: RentPeriod, amount: number) {
    if (!id) return;
    if (!amount || amount <= 0) {
      setErr("Укажите сумму поступления");
      return;
    }
    setErr(null);
    setMsg(null);
    setBusyPeriodId(period.id);
    try {
      await apiJson(`/api/properties/${id}/leases/${lease.id}/periods/${period.id}/payments`, {
        method: "POST",
        body: JSON.stringify({ amount }),
      });
      await reloadLeases();
      setPayDrafts((prev) => ({ ...prev, [period.id]: "" }));
      setMsg("Оплата зафиксирована");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Ошибка");
    } finally {
      setBusyPeriodId(null);
    }
  }

  async function terminateLease(lease: Lease) {
    if (!id) return;
    const today = new Date().toISOString().slice(0, 10);
    setErr(null);
    setMsg(null);
    try {
      await apiJson(`/api/properties/${id}/leases/${lease.id}`, {
        method: "PATCH",
        body: JSON.stringify({ terminated_at: today }),
      });
      await reloadLeases();
      setMsg("Договор отмечен расторгнутым — новые начисления не создаются");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Ошибка");
    }
  }

  async function sendTest(kind: "tenant-reminder" | "owner-paid" | "owner-not-paid") {
    if (!testPeriodId) {
      setErr("Выберите начисление для теста");
      return;
    }
    const toEmail = kind === "tenant-reminder" ? testToEmail : testOwnerEmail;
    if (!toEmail.trim()) {
      setErr("Укажите email получателя");
      return;
    }
    setErr(null);
    setMsg(null);
    setTestSending(true);
    try {
      await apiJson<{ detail: string }>(`/api/email/test/${kind}`, {
        method: "POST",
        body: JSON.stringify({ period_id: testPeriodId, to_email: toEmail.trim() }),
      });
      setMsg("Тестовое письмо отправлено.");
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
              placeholder="Например: Кирова, 1 этаж — 256,3 кв.м"
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
                Вручную или загрузите .txt (ФИО, email, даты, сумма аренды, день оплаты). По договору
                автоматически создаются ежемесячные начисления.
              </p>
            </div>
            <form onSubmit={addLease} className="space-y-5 p-6 sm:p-8">
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="label">ФИО / арендатор</label>
                  <input
                    className="input-field"
                    value={tenantName}
                    onChange={(e) => setTenantName(e.target.value)}
                    placeholder="ИП Иванов Иван"
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
                  <label className="label">Сумма аренды в месяц, ₽</label>
                  <input
                    type="number"
                    min="1"
                    className="input-field"
                    value={rentAmount}
                    onChange={(e) => setRentAmount(e.target.value)}
                    placeholder="35000"
                  />
                </div>
                <div>
                  <label className="label">День оплaты (число месяца)</label>
                  <input
                    type="number"
                    min="1"
                    max="31"
                    className="input-field"
                    value={paymentDay}
                    onChange={(e) => setPaymentDay(e.target.value)}
                    placeholder="17"
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
                <div>
                  <label className="label">№ договора (необязательно)</label>
                  <input
                    className="input-field"
                    value={contractNumber}
                    onChange={(e) => setContractNumber(e.target.value)}
                    placeholder="8"
                  />
                </div>
                <div>
                  <label className="label">Дата договора (необязательно)</label>
                  <input
                    type="date"
                    className="input-field"
                    value={contractDate}
                    onChange={(e) => setContractDate(e.target.value)}
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
                {file && <p className="mt-3 text-xs font-medium text-brand-700">Выбран: {file.name}</p>}
              </div>

              <button type="submit" className="btn-primary w-full justify-center py-3">
                Добавить аренду
              </button>
            </form>
          </section>

          {leases.length > 0 && (
            <section>
              <h3 className="mb-4 font-display text-base font-semibold text-ink-900">Аренда и начисления</h3>
              <ul className="space-y-5">
                {leases.map((l) => (
                  <li key={l.id} className="card-elevated p-5 sm:p-6">
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                      <div className="min-w-0">
                        <p className="font-medium text-ink-900">{l.tenant_name}</p>
                        <p className="mt-1 text-xs text-ink-500">{l.tenant_email}</p>
                        <p className="mt-1 text-xs text-ink-500">
                          {money(l.rent_amount)}/мес · оплата до {l.payment_day} числа · {l.rent_start} — {l.rent_end}
                          {l.contract_number ? ` · договор №${l.contract_number}` : ""}
                        </p>
                      </div>
                      {l.terminated_at ? (
                        <span className="badge shrink-0 bg-ink-100 text-ink-600 ring-1 ring-ink-900/10">
                          Расторгнут {l.terminated_at}
                        </span>
                      ) : (
                        <button
                          type="button"
                          onClick={() => void terminateLease(l)}
                          className="btn-secondary shrink-0 py-2 text-xs"
                        >
                          Расторгнуть
                        </button>
                      )}
                    </div>

                    {l.periods.length > 0 && (
                      <div className="mt-4 overflow-hidden rounded-xl border border-ink-900/[0.06]">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="bg-surface-muted text-left text-xs uppercase tracking-wider text-ink-500">
                              <th className="px-3 py-2 font-semibold">Период</th>
                              <th className="px-3 py-2 font-semibold">Оплатить до</th>
                              <th className="px-3 py-2 font-semibold">Начислено</th>
                              <th className="px-3 py-2 font-semibold">Оплачено</th>
                              <th className="px-3 py-2 font-semibold">Статус</th>
                              <th className="px-3 py-2 font-semibold">Внести оплату</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-ink-900/[0.05]">
                            {l.periods.map((p) => {
                              const remaining = Math.max(p.amount_due - p.amount_paid, 0);
                              const draft = payDrafts[p.id] ?? "";
                              return (
                                <tr key={p.id} className="text-ink-700">
                                  <td className="px-3 py-2 whitespace-nowrap">{monthLabel(p.year, p.month)}</td>
                                  <td className="px-3 py-2 whitespace-nowrap text-ink-500">{p.due_date}</td>
                                  <td className="px-3 py-2 whitespace-nowrap">{money(p.amount_due)}</td>
                                  <td className="px-3 py-2 whitespace-nowrap">{money(p.amount_paid)}</td>
                                  <td className="px-3 py-2">
                                    <span className={`badge ring-1 ${payStyle[p.status] ?? "bg-ink-100"}`}>
                                      {payLabel[p.status] ?? p.status}
                                    </span>
                                  </td>
                                  <td className="px-3 py-2">
                                    {p.status === "paid" ? (
                                      <span className="text-xs text-emerald-700">—</span>
                                    ) : (
                                      <div className="flex items-center gap-1.5">
                                        <input
                                          type="number"
                                          min="1"
                                          className="input-field h-9 w-24 py-1 text-sm"
                                          value={draft}
                                          placeholder={String(remaining)}
                                          onChange={(e) =>
                                            setPayDrafts((prev) => ({ ...prev, [p.id]: e.target.value }))
                                          }
                                        />
                                        <button
                                          type="button"
                                          disabled={busyPeriodId === p.id}
                                          onClick={() =>
                                            void recordPayment(l, p, Number(draft || remaining))
                                          }
                                          className="btn-secondary shrink-0 px-3 py-1.5 text-xs"
                                        >
                                          {busyPeriodId === p.id ? "…" : "ОК"}
                                        </button>
                                      </div>
                                    )}
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {allPeriods.length > 0 && (
            <section className="rounded-2xl border border-amber-200/80 bg-gradient-to-br from-amber-50/90 to-orange-50/40 p-6 sm:p-8">
              <h3 className="font-display text-base font-semibold text-amber-950">Тестовая отправка почты</h3>
              <p className="mt-1 text-sm text-amber-900/80">
                Те же шаблоны, что в проде: напоминание арендатору об оплате за период; владельцу — при
                подтверждении оплаты или при отсутствии оплаты (как после срока).
              </p>
              <div className="mt-5 space-y-6">
                <div>
                  <label className="label text-amber-900/70">Начисление (контекст письма)</label>
                  <select
                    className="input-field"
                    value={testPeriodId}
                    onChange={(e) => {
                      const pid = e.target.value;
                      setTestPeriodId(pid);
                      const found = allPeriods.find((x) => x.period.id === pid);
                      if (found) setTestToEmail(found.lease.tenant_email);
                    }}
                  >
                    {allPeriods.map(({ lease, period }) => (
                      <option key={period.id} value={period.id}>
                        {lease.tenant_name} · {monthLabel(period.year, period.month)} · {money(period.amount_due)}
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
                    onClick={() => void sendTest("tenant-reminder")}
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
                      onClick={() => void sendTest("owner-paid")}
                      className="rounded-xl border border-emerald-200 bg-gradient-to-br from-emerald-50 to-teal-50/80 px-4 py-3 text-sm font-semibold text-emerald-900 shadow-sm transition hover:border-emerald-300 disabled:opacity-60"
                    >
                      {testSending ? "…" : "Оплата подтверждена (тест)"}
                    </button>
                    <button
                      type="button"
                      disabled={testSending}
                      onClick={() => void sendTest("owner-not-paid")}
                      className="rounded-xl border border-rose-200 bg-gradient-to-br from-rose-50 to-orange-50/50 px-4 py-3 text-sm font-semibold text-rose-900 shadow-sm transition hover:border-rose-300 disabled:opacity-60"
                    >
                      {testSending ? "…" : "Нет оплаты (тест)"}
                    </button>
                  </div>
                </div>
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}

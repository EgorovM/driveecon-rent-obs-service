import { FormEvent, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { AlertError } from "../components/Alert";
import { BrandMark } from "../components/BrandMark";
import { useAuth } from "../auth";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation() as { state?: { from?: string } };
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setErr(null);
    setBusy(true);
    try {
      await login(username.trim(), password);
      navigate(location.state?.from ?? "/", { replace: true });
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Ошибка входа");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto mt-10 max-w-sm animate-fade-in">
      <div className="mb-8 flex flex-col items-center gap-3 text-center">
        <BrandMark />
        <div>
          <h1 className="font-display text-2xl font-bold tracking-tight text-ink-900">Drivee</h1>
          <p className="text-sm text-ink-500">Вход в систему контроля аренды</p>
        </div>
      </div>

      <form
        onSubmit={onSubmit}
        className="space-y-4 rounded-2xl border border-ink-900/[0.06] bg-white/70 p-6 shadow-sm backdrop-blur"
      >
        {err && <AlertError>{err}</AlertError>}
        <label className="block">
          <span className="mb-1 block text-sm font-medium text-ink-700">Логин</span>
          <input
            type="text"
            autoComplete="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="w-full rounded-xl border border-ink-900/10 bg-white px-3 py-2 text-sm outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-400/30"
            required
          />
        </label>
        <label className="block">
          <span className="mb-1 block text-sm font-medium text-ink-700">Пароль</span>
          <input
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-xl border border-ink-900/10 bg-white px-3 py-2 text-sm outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-400/30"
            required
          />
        </label>
        <button
          type="submit"
          disabled={busy}
          className="w-full rounded-xl bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
        >
          {busy ? "Входим…" : "Войти"}
        </button>
      </form>
    </div>
  );
}

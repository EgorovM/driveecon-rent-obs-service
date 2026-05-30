import type { ReactNode } from "react";
import { Link, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { ConfirmPage } from "./pages/ConfirmPage";
import { HomePage } from "./pages/HomePage";
import { PropertyPage } from "./pages/PropertyPage";
import { LoginPage } from "./pages/LoginPage";
import { BrandMark } from "./components/BrandMark";
import { AuthProvider, useAuth } from "./auth";

function Layout({ children }: { children: ReactNode }) {
  const { token, username, logout } = useAuth();
  return (
    <div className="min-h-screen flex flex-col">
      <header className="sticky top-0 z-50 border-b border-white/40 bg-white/70 backdrop-blur-xl supports-[backdrop-filter]:bg-white/60">
        <div className="page-container flex items-center justify-between gap-4 py-4">
          <Link to="/" className="group flex items-center gap-3">
            <BrandMark className="transition-transform duration-300 group-hover:scale-105" />
            <div>
              <span className="font-display text-lg font-bold tracking-tight text-ink-900">Drivee</span>
              <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-brand-600/90">
                rental
              </p>
            </div>
          </Link>
          <nav className="flex items-center gap-4 text-sm font-medium text-ink-600">
            <span className="hidden text-ink-400 sm:inline">Мониторинг аренды и платежей</span>
            {token && (
              <div className="flex items-center gap-3">
                <span className="text-ink-500">{username}</span>
                <button
                  onClick={logout}
                  className="rounded-lg border border-ink-900/10 bg-white px-3 py-1.5 text-xs font-semibold text-ink-700 transition hover:bg-ink-50"
                >
                  Выйти
                </button>
              </div>
            )}
          </nav>
        </div>
        <div className="h-px w-full bg-gradient-to-r from-transparent via-brand-400/30 to-transparent" />
      </header>

      <main className="flex-1 page-container py-10 sm:py-12">{children}</main>

      <footer className="mt-auto border-t border-ink-900/[0.06] bg-white/40 backdrop-blur-sm">
        <div className="page-container py-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-ink-500">
          <p>Напоминания за 3 дня · письма арендаторам и владельцам</p>
          <p className="font-medium text-ink-400">© {new Date().getFullYear()} Drivee</p>
        </div>
      </footer>
    </div>
  );
}

function RequireAuth({ children }: { children: ReactNode }) {
  const { token } = useAuth();
  const location = useLocation();
  if (!token) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return <>{children}</>;
}

export default function App() {
  return (
    <AuthProvider>
      <Layout>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/confirm/:token" element={<ConfirmPage />} />
          <Route path="/" element={<RequireAuth><HomePage /></RequireAuth>} />
          <Route path="/properties/new" element={<RequireAuth><PropertyPage /></RequireAuth>} />
          <Route path="/properties/:id" element={<RequireAuth><PropertyPage /></RequireAuth>} />
        </Routes>
      </Layout>
    </AuthProvider>
  );
}

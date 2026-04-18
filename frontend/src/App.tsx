import type { ReactNode } from "react";
import { Link, Route, Routes } from "react-router-dom";
import { ConfirmPage } from "./pages/ConfirmPage";
import { HomePage } from "./pages/HomePage";
import { PropertyPage } from "./pages/PropertyPage";
import { BrandMark } from "./components/BrandMark";

function Layout({ children }: { children: ReactNode }) {
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
          <nav className="hidden sm:flex items-center gap-6 text-sm font-medium text-ink-600">
            <span className="text-ink-400">Мониторинг аренды и платежей</span>
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

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/properties/new" element={<PropertyPage />} />
        <Route path="/properties/:id" element={<PropertyPage />} />
        <Route path="/confirm/:token" element={<ConfirmPage />} />
      </Routes>
    </Layout>
  );
}

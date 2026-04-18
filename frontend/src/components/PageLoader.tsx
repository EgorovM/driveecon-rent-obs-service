export function PageLoader({ label = "Загрузка…" }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-20 animate-fade-in">
      <div className="relative h-12 w-12">
        <div className="absolute inset-0 rounded-2xl border-2 border-brand-200/80" />
        <div className="absolute inset-0 animate-shimmer rounded-2xl border-2 border-transparent border-t-brand-500 border-r-brand-400/40" />
      </div>
      <p className="text-sm font-medium text-ink-500">{label}</p>
    </div>
  );
}

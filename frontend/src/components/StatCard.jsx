export default function StatCard({ label, value, accent }) {
  return (
    <div className="rounded-lg border border-ink-700 bg-ink-900 px-4 py-3 shadow-panel">
      <p className="text-xs text-text-faint">{label}</p>
      <p
        className="mt-1 font-mono text-2xl font-semibold tabular-nums"
        style={accent ? { color: accent } : undefined}
      >
        {value}
      </p>
    </div>
  );
}

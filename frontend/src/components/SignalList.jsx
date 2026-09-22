// Renders signals[] - the human-readable justification trail behind a score.
// signal.type is one of RULE | ML | PII (section 6). severity is 0-100 or
// null; confidence is 0-1 or null (ML only).

const TYPE_STYLE = {
  RULE: "text-accent",
  ML: "text-signal-sanitize",
  PII: "text-signal-block",
};

export default function SignalList({ signals = [] }) {
  if (!signals.length) {
    return <p className="text-sm text-text-faint">No contributing signals returned.</p>;
  }

  return (
    <ul className="space-y-2">
      {signals.map((signal, i) => (
        <li
          key={i}
          className="flex items-start justify-between gap-3 rounded-md border border-ink-700 bg-ink-900 px-3 py-2"
        >
          <div className="flex items-start gap-2.5 min-w-0">
            <span
              className={`mt-0.5 shrink-0 font-mono text-[10px] font-semibold tracking-wide ${
                TYPE_STYLE[signal.type] || "text-text-muted"
              }`}
            >
              {signal.type}
            </span>
            <span className="text-sm text-text-primary break-words">{signal.message}</span>
          </div>
          <span className="shrink-0 font-mono text-xs text-text-muted tabular-nums">
            {signal.severity != null && `+${signal.severity}`}
            {signal.confidence != null && `${(signal.confidence * 100).toFixed(0)}%`}
          </span>
        </li>
      ))}
    </ul>
  );
}

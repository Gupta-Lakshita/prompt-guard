// Displays the backend's decision string verbatim (ALLOW | SANITIZE | BLOCK).
// Never invents alternate spellings - see handoff doc section 6.

const STYLES = {
  ALLOW: "bg-signal-allow-dim text-signal-allow border-signal-allow/30",
  SANITIZE: "bg-signal-sanitize-dim text-signal-sanitize border-signal-sanitize/30",
  BLOCK: "bg-signal-block-dim text-signal-block border-signal-block/30",
};

const DOT = {
  ALLOW: "bg-signal-allow",
  SANITIZE: "bg-signal-sanitize",
  BLOCK: "bg-signal-block",
};

export default function DecisionBadge({ decision, size = "md" }) {
  const style = STYLES[decision] || "bg-ink-800 text-text-muted border-ink-700";
  const dot = DOT[decision] || "bg-text-faint";
  const padding = size === "lg" ? "px-4 py-2 text-base" : "px-2.5 py-1 text-xs";

  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full border font-mono font-medium tracking-tight ${style} ${padding}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${dot}`} aria-hidden="true" />
      {decision || "UNKNOWN"}
    </span>
  );
}

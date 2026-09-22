// Displays the backend's threats[] array. Allowed values (section 6):
// PROMPT_INJECTION | JAILBREAK | SENSITIVE_DATA | SOCIAL_ENGINEERING

const LABELS = {
  PROMPT_INJECTION: "Prompt injection",
  JAILBREAK: "Jailbreak",
  SENSITIVE_DATA: "Sensitive data",
  SOCIAL_ENGINEERING: "Social engineering",
};

export default function ThreatChips({ threats = [] }) {
  if (!threats.length) {
    return <span className="text-sm text-text-faint">No threat categories flagged.</span>;
  }

  return (
    <div className="flex flex-wrap gap-1.5">
      {threats.map((t) => (
        <span
          key={t}
          className="rounded border border-ink-600 bg-ink-800 px-2 py-0.5 text-xs text-text-primary font-mono"
        >
          {LABELS[t] || t}
        </span>
      ))}
    </div>
  );
}

// Only renders when sanitized_prompt is not null, per handoff doc section 6.

export default function SanitizedPromptView({ originalPrompt, sanitizedPrompt }) {
  if (sanitizedPrompt == null) return null;

  return (
    <div className="space-y-2">
      <p className="text-xs font-mono uppercase tracking-wide text-text-faint">
        Sanitized before forwarding
      </p>
      <div className="rounded-md border border-ink-700 bg-ink-900 p-3">
        <p className="mb-1 text-[11px] text-text-faint">Original</p>
        <p className="mb-3 font-mono text-sm text-text-muted line-through decoration-signal-block/50">
          {originalPrompt}
        </p>
        <p className="mb-1 text-[11px] text-text-faint">Forwarded</p>
        <p className="font-mono text-sm text-signal-allow">{sanitizedPrompt}</p>
      </div>
    </div>
  );
}

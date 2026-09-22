import { Fragment, useMemo, useState } from "react";
import DecisionBadge from "./DecisionBadge.jsx";
import ThreatChips from "./ThreatChips.jsx";
import SignalList from "./SignalList.jsx";
import SanitizedPromptView from "./SanitizedPromptView.jsx";

const DECISIONS = ["ALL", "ALLOW", "SANITIZE", "BLOCK"];

function formatTime(ts) {
  try {
    return new Date(ts).toLocaleString();
  } catch {
    return ts;
  }
}

export default function EventLogTable({ events = [] }) {
  const [query, setQuery] = useState("");
  const [decisionFilter, setDecisionFilter] = useState("ALL");
  const [expandedId, setExpandedId] = useState(null);

  const filtered = useMemo(() => {
    return events.filter((e) => {
      const matchesDecision = decisionFilter === "ALL" || e.decision === decisionFilter;
      const matchesQuery =
        query.trim() === "" ||
        e.original_prompt?.toLowerCase().includes(query.toLowerCase()) ||
        e.scan_id?.toLowerCase().includes(query.toLowerCase());
      return matchesDecision && matchesQuery;
    });
  }, [events, query, decisionFilter]);

  return (
    <div className="space-y-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search prompt text or scan ID"
          className="w-full rounded-md border border-ink-700 bg-ink-900 px-3 py-2 text-sm text-text-primary placeholder:text-text-faint focus:border-accent sm:max-w-xs"
        />
        <div className="flex gap-1.5">
          {DECISIONS.map((d) => (
            <button
              key={d}
              onClick={() => setDecisionFilter(d)}
              className={`rounded-md border px-2.5 py-1.5 font-mono text-xs transition-colors ${
                decisionFilter === d
                  ? "border-accent bg-accent/10 text-accent"
                  : "border-ink-700 bg-ink-900 text-text-muted hover:text-text-primary"
              }`}
            >
              {d}
            </button>
          ))}
        </div>
      </div>

      <div className="thin-scroll overflow-x-auto rounded-lg border border-ink-700">
        <table className="w-full min-w-[640px] border-collapse text-left text-sm">
          <thead>
            <tr className="border-b border-ink-700 bg-ink-900 text-xs text-text-faint">
              <th className="px-3 py-2 font-normal">Time</th>
              <th className="px-3 py-2 font-normal">Prompt</th>
              <th className="px-3 py-2 font-normal">Score</th>
              <th className="px-3 py-2 font-normal">Decision</th>
              <th className="px-3 py-2 font-normal">Threats</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 && (
              <tr>
                <td colSpan={5} className="px-3 py-8 text-center text-text-faint">
                  No events match this search.
                </td>
              </tr>
            )}
            {filtered.map((e) => {
              const isOpen = expandedId === e.scan_id;
              return (
                <Fragment key={e.scan_id}>
                  <tr
                    onClick={() => setExpandedId(isOpen ? null : e.scan_id)}
                    className="cursor-pointer border-b border-ink-700 bg-ink-950 hover:bg-ink-800"
                  >
                    <td className="px-3 py-2.5 font-mono text-xs text-text-muted whitespace-nowrap">
                      {formatTime(e.timestamp)}
                    </td>
                    <td className="max-w-xs truncate px-3 py-2.5 text-text-primary">
                      {e.original_prompt}
                    </td>
                    <td className="px-3 py-2.5 font-mono tabular-nums">{e.risk_score}</td>
                    <td className="px-3 py-2.5">
                      <DecisionBadge decision={e.decision} />
                    </td>
                    <td className="px-3 py-2.5">
                      <ThreatChips threats={e.threats} />
                    </td>
                  </tr>
                  {isOpen && (
                    <tr className="border-b border-ink-700 bg-ink-900">
                      <td colSpan={5} className="space-y-4 px-4 py-4">
                        <SignalList signals={e.signals} />
                        <SanitizedPromptView
                          originalPrompt={e.original_prompt}
                          sanitizedPrompt={e.sanitized_prompt}
                        />
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

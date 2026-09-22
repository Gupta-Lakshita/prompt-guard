import { useEffect, useMemo, useState } from "react";
import StatCard from "../components/StatCard.jsx";
import EventLogTable from "../components/EventLogTable.jsx";
import { MOCK_EVENT_LOG } from "../services/mockData.js";
import { BASE_URL } from "../services/api.js";

export default function DashboardPage() {
  const [events, setEvents] = useState([]);
  const [source, setSource] = useState("loading"); // loading | live | mock

  useEffect(() => {
    let cancelled = false;

    async function loadEvents() {
      try {
        // Not part of the Micro-stage shared contract yet (only /scan is
        // defined there). If/when the backend exposes a log-listing
        // endpoint, point this at it - falls back to mock data until then.
        const res = await fetch(`${BASE_URL}/events`);
        if (!res.ok) throw new Error("no events endpoint yet");
        const data = await res.json();
        if (!cancelled) {
          setEvents(data);
          setSource("live");
        }
      } catch {
        if (!cancelled) {
          setEvents(MOCK_EVENT_LOG);
          setSource("mock");
        }
      }
    }

    loadEvents();
    return () => {
      cancelled = true;
    };
  }, []);

  const stats = useMemo(() => {
    const total = events.length;
    const count = (d) => events.filter((e) => e.decision === d).length;
    return {
      total,
      allow: count("ALLOW"),
      sanitize: count("SANITIZE"),
      block: count("BLOCK"),
    };
  }, [events]);

  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      <header className="mb-8 flex items-start justify-between gap-4">
        <div>
          <h1 className="font-mono text-xl font-semibold text-text-primary">Security event log</h1>
          <p className="mt-1 text-sm text-text-muted">
            Every scanned prompt, its decision and the signals behind it.
          </p>
        </div>
        {source === "mock" && (
          <span className="shrink-0 rounded-md border border-accent/30 bg-accent-dim px-2.5 py-1 text-xs text-accent">
            Mock data
          </span>
        )}
      </header>

      <div className="mb-8 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard label="Total scans" value={stats.total} />
        <StatCard label="Allowed" value={stats.allow} accent="#34D399" />
        <StatCard label="Sanitized" value={stats.sanitize} accent="#F2B84B" />
        <StatCard label="Blocked" value={stats.block} accent="#F0576A" />
      </div>

      {source === "loading" ? (
        <p className="text-sm text-text-muted">Loading event log...</p>
      ) : (
        <EventLogTable events={events} />
      )}
    </div>
  );
}

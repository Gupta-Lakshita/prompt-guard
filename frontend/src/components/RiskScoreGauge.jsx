// Renders the 0-100 risk_score as an arc gauge, colored by the same bands
// the backend uses to decide: 0-34 allow, 35-69 sanitize, 70-100 block.

function bandFor(score) {
  if (score >= 70) return { color: "#F0576A", label: "BLOCK", track: "#341018" };
  if (score >= 35) return { color: "#F2B84B", label: "SANITIZE", track: "#332708" };
  return { color: "#34D399", label: "ALLOW", track: "#0F2E24" };
}

export default function RiskScoreGauge({ score = 0, size = 128 }) {
  const clamped = Math.max(0, Math.min(100, score));
  const { color, track } = bandFor(clamped);

  const radius = 52;
  const circumference = 2 * Math.PI * radius;
  // Gauge sweeps 270 degrees (like a dial), starting bottom-left.
  const sweep = 0.75 * circumference;
  const filled = (clamped / 100) * sweep;

  return (
    <div
      className="relative flex items-center justify-center"
      style={{ width: size, height: size }}
      role="img"
      aria-label={`Risk score ${clamped} out of 100`}
    >
      <svg viewBox="0 0 140 140" width={size} height={size} className="-rotate-[135deg]">
        <circle
          cx="70"
          cy="70"
          r={radius}
          fill="none"
          stroke={track}
          strokeWidth="10"
          strokeDasharray={`${sweep} ${circumference}`}
          strokeLinecap="round"
        />
        <circle
          cx="70"
          cy="70"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeDasharray={`${filled} ${circumference}`}
          strokeLinecap="round"
          style={{ transition: "stroke-dasharray 500ms ease-out" }}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="font-mono text-3xl font-semibold tabular-nums" style={{ color }}>
          {clamped}
        </span>
        <span className="text-[10px] text-text-faint">/ 100</span>
      </div>
    </div>
  );
}

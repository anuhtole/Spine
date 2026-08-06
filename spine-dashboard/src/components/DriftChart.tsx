/**
 * Drift score over a session's evaluations.
 *
 * Inline SVG, no external deps. Plots drift_score_after on the y-axis
 * (0..1), evaluation index on the x-axis, with horizontal reference
 * lines at the flag and block thresholds.
 */
import type { ReactElement } from "react";

export interface DriftPoint {
  drift_score_after: number;
  alignment: string;
}

interface Props {
  points: DriftPoint[];
  flagThreshold?: number;
  blockThreshold?: number;
  height?: number;
}

const PAD_L = 36;
const PAD_R = 16;
const PAD_T = 16;
const PAD_B = 26;
const W = 640;

const ALIGN_COLOR: Record<string, string> = {
  aligned: "#34d399", // emerald-400
  drifted: "#fbbf24", // amber-400
  divergent: "#fb7185", // rose-400
};

export function DriftChart({
  points,
  flagThreshold = 0.4,
  blockThreshold = 0.6,
  height = 220,
}: Props): ReactElement {
  const innerW = W - PAD_L - PAD_R;
  const innerH = height - PAD_T - PAD_B;
  const n = Math.max(points.length, 1);

  const xAt = (i: number) =>
    PAD_L + (n === 1 ? innerW / 2 : (i / (n - 1)) * innerW);
  const yAt = (v: number) => PAD_T + (1 - v) * innerH;

  // Build polyline path
  const pathD =
    points.length === 0
      ? ""
      : points
          .map((p, i) => `${i === 0 ? "M" : "L"}${xAt(i)},${yAt(p.drift_score_after)}`)
          .join(" ");

  // Vertical y-axis ticks at 0.0, 0.5, 1.0
  const yTicks = [0, 0.25, 0.5, 0.75, 1.0];

  return (
    <svg
      viewBox={`0 0 ${W} ${height}`}
      className="w-full text-spine-muted"
      role="img"
      aria-label="Session drift score over time"
    >
      {/* y-axis grid */}
      {yTicks.map((t) => (
        <g key={t}>
          <line
            x1={PAD_L}
            x2={W - PAD_R}
            y1={yAt(t)}
            y2={yAt(t)}
            stroke="currentColor"
            strokeOpacity={t === 0 ? 0.4 : 0.1}
          />
          <text
            x={PAD_L - 8}
            y={yAt(t) + 4}
            fontSize={10}
            textAnchor="end"
            fill="currentColor"
            opacity={0.6}
          >
            {t.toFixed(2)}
          </text>
        </g>
      ))}

      {/* Flag threshold band (between flag and block) */}
      <rect
        x={PAD_L}
        y={yAt(blockThreshold)}
        width={innerW}
        height={yAt(flagThreshold) - yAt(blockThreshold)}
        fill="#fbbf24"
        opacity={0.06}
      />
      {/* Block threshold band (above block) */}
      <rect
        x={PAD_L}
        y={yAt(1)}
        width={innerW}
        height={yAt(blockThreshold) - yAt(1)}
        fill="#fb7185"
        opacity={0.08}
      />

      {/* Threshold reference lines */}
      <line
        x1={PAD_L}
        x2={W - PAD_R}
        y1={yAt(flagThreshold)}
        y2={yAt(flagThreshold)}
        stroke="#fbbf24"
        strokeOpacity={0.5}
        strokeDasharray="3 3"
      />
      <line
        x1={PAD_L}
        x2={W - PAD_R}
        y1={yAt(blockThreshold)}
        y2={yAt(blockThreshold)}
        stroke="#fb7185"
        strokeOpacity={0.6}
        strokeDasharray="3 3"
      />
      <text x={W - PAD_R} y={yAt(flagThreshold) - 4} fontSize={9} textAnchor="end" fill="#fbbf24">
        flag {flagThreshold.toFixed(2)}
      </text>
      <text x={W - PAD_R} y={yAt(blockThreshold) - 4} fontSize={9} textAnchor="end" fill="#fb7185">
        block {blockThreshold.toFixed(2)}
      </text>

      {/* x-axis baseline */}
      <line
        x1={PAD_L}
        x2={W - PAD_R}
        y1={yAt(0)}
        y2={yAt(0)}
        stroke="currentColor"
        strokeOpacity={0.4}
      />

      {/* Line path */}
      {pathD ? (
        <path
          d={pathD}
          fill="none"
          stroke="#a5b4fc"
          strokeWidth={2}
          strokeLinejoin="round"
          strokeLinecap="round"
        />
      ) : null}

      {/* Points, color-coded by alignment */}
      {points.map((p, i) => (
        <circle
          key={i}
          cx={xAt(i)}
          cy={yAt(p.drift_score_after)}
          r={4}
          fill={ALIGN_COLOR[p.alignment] ?? "#a5b4fc"}
          stroke="#0a0a0a"
          strokeWidth={1}
        >
          <title>
            #{i + 1} · {p.alignment} · drift {p.drift_score_after.toFixed(3)}
          </title>
        </circle>
      ))}

      {/* x-axis label */}
      <text
        x={PAD_L + innerW / 2}
        y={height - 6}
        fontSize={10}
        textAnchor="middle"
        fill="currentColor"
        opacity={0.5}
      >
        evaluation #
      </text>

      {/* Empty-state label */}
      {points.length === 0 ? (
        <text
          x={PAD_L + innerW / 2}
          y={PAD_T + innerH / 2}
          fontSize={11}
          textAnchor="middle"
          fill="currentColor"
          opacity={0.5}
        >
          no plan evaluations yet
        </text>
      ) : null}
    </svg>
  );
}

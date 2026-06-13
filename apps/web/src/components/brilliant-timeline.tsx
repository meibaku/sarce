"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceArea,
} from "recharts";
import type { TimelinePoint } from "@/types/chess";

interface BrilliantTimelineProps {
  points: TimelinePoint[];
  targetMin: number;
  targetMax: number;
}

export function BrilliantTimeline({
  points,
  targetMin,
  targetMax,
}: BrilliantTimelineProps) {
  if (points.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center rounded-lg border border-dashed border-white/10 text-sm text-foreground/40">
        Awaiting analyzed games
      </div>
    );
  }

  const data = points.map((p) => ({
    date: p.date ? new Date(p.date).toLocaleDateString() : "?",
    brilliantPct: p.brilliantPct,
    opponent: p.opponent,
  }));

  return (
    <div className="h-48 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <ReferenceArea
            y1={targetMin}
            y2={targetMax}
            fill="var(--brilliant)"
            fillOpacity={0.15}
          />
          <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#888" }} />
          <YAxis
            domain={[0, 20]}
            tick={{ fontSize: 11, fill: "#888" }}
            tickFormatter={(v) => `${v}%`}
          />
          <Tooltip
            contentStyle={{
              background: "var(--surface)",
              border: "1px solid rgba(255,255,255,0.1)",
            }}
            formatter={(value: number) => [`${value.toFixed(1)}%`, "Brilliant"]}
            labelFormatter={(_, payload) =>
              payload?.[0]?.payload?.opponent
                ? `vs ${payload[0].payload.opponent}`
                : ""
            }
          />
          <Line
            type="monotone"
            dataKey="brilliantPct"
            stroke="var(--brilliant)"
            strokeWidth={2}
            dot={{ fill: "var(--brilliant)", r: 3 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

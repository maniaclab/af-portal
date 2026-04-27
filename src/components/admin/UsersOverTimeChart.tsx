"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface DataPoint {
  date: string;
  count: number;
}

export default function UsersOverTimeChart({ data }: { data: DataPoint[] }) {
  const ticks = data
    .filter((_, i) => i % 6 === 0)
    .map((d) => d.date);

  return (
    <ResponsiveContainer width="100%" height={420}>
      <LineChart data={data} margin={{ top: 10, right: 30, left: 10, bottom: 60 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.3} />
        <XAxis
          dataKey="date"
          ticks={ticks}
          angle={-30}
          textAnchor="end"
          interval={0}
          label={{ value: "Month", position: "insideBottom", offset: -50 }}
        />
        <YAxis
          label={{ value: "Number of users", angle: -90, position: "insideLeft" }}
        />
        <Tooltip />
        <Line
          type="linear"
          dataKey="count"
          stroke="#0d6efd"
          strokeWidth={2}
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

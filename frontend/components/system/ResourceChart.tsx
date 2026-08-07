'use client';

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

interface ResourceChartData {
  time: string;
  cpu: number;
  gpu?: number;
  ram: number;
  diskRead?: number;
  diskWrite?: number;
}

interface ResourceChartProps {
  data: ResourceChartData[];
}

export function ResourceChart({ data }: ResourceChartProps) {
  if (data.length === 0) {
    return (
      <div className="h-[300px] flex items-center justify-center text-muted-foreground">
        Waiting for data...
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
        <XAxis
          dataKey="time"
          stroke="hsl(var(--muted-foreground))"
          fontSize={12}
        />
        <YAxis
          stroke="hsl(var(--muted-foreground))"
          fontSize={12}
          domain={[0, 100]}
          tickFormatter={(value) => `${value}%`}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: 'hsl(var(--card))',
            border: '1px solid hsl(var(--border))',
            borderRadius: '8px',
          }}
        />
        <Legend />
        <Line
          type="monotone"
          dataKey="cpu"
          stroke="hsl(var(--primary))"
          strokeWidth={2}
          dot={false}
          name="CPU"
          isAnimationActive={false}
        />
        <Line
          type="monotone"
          dataKey="gpu"
          stroke="#0ea5e9"
          strokeWidth={2}
          dot={false}
          name="GPU"
          isAnimationActive={false}
        />
        <Line
          type="monotone"
          dataKey="ram"
          stroke="#22c55e"
          strokeWidth={2}
          dot={false}
          name="RAM"
          isAnimationActive={false}
        />
        <Line
          type="monotone"
          dataKey="diskRead"
          stroke="#f59e0b"
          strokeWidth={2}
          dot={false}
          name="Disk Read"
          isAnimationActive={false}
        />
        <Line
          type="monotone"
          dataKey="diskWrite"
          stroke="#ef4444"
          strokeWidth={2}
          dot={false}
          name="Disk Write"
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
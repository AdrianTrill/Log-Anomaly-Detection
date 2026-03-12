"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

const LEVEL_BAR_COLORS: Record<string, string> = {
  ERROR: "#ef4444",
  FATAL: "#dc2626",
  CRITICAL: "#dc2626",
  WARN: "#f59e0b",
  WARNING: "#f59e0b",
  INFO: "#10b981",
  DEBUG: "#0ea5e9",
  TRACE: "#a855f7",
};

interface LevelChartProps {
  distribution: Record<string, number>;
}

export function LevelChart({ distribution }: LevelChartProps) {
  const data = Object.entries(distribution)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value);

  if (data.length === 0) return null;

  const isSingleLevel = data.length === 1;
  const totalEntries = data.reduce((sum, d) => sum + d.value, 0);
  const chartHeight = isSingleLevel ? 160 : 280;

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-sm font-semibold">Log Level Distribution</CardTitle>
            <CardDescription className="text-xs">
              {isSingleLevel
                ? `All ${totalEntries.toLocaleString()} entries are ${data[0].name}`
                : "Breakdown of entries by severity level"
              }
            </CardDescription>
          </div>
          {isSingleLevel && (
            <Badge variant="secondary" className="text-[10px] font-normal py-0">
              100% {data[0].name}
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="pt-2">
        <ResponsiveContainer width="100%" height={chartHeight}>
          <BarChart
            data={data}
            margin={{ top: 8, right: 8, bottom: 4, left: -8 }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="var(--color-border)"
              vertical={false}
            />
            <XAxis
              dataKey="name"
              fontSize={11}
              tick={{ fill: "var(--color-muted-foreground)" }}
              axisLine={false}
              tickLine={false}
              dy={4}
            />
            <YAxis
              fontSize={11}
              tick={{ fill: "var(--color-muted-foreground)" }}
              axisLine={false}
              tickLine={false}
              width={40}
            />
            <Tooltip
              cursor={{ fill: "var(--color-muted)", opacity: 0.2 }}
              contentStyle={{
                backgroundColor: "var(--color-popover)",
                border: "1px solid var(--color-border)",
                borderRadius: "8px",
                fontSize: "12px",
                boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
                padding: "8px 12px",
              }}
              labelStyle={{ color: "var(--color-foreground)", fontWeight: 600, marginBottom: "2px" }}
              itemStyle={{ color: "var(--color-muted-foreground)" }}
            />
            <Bar dataKey="value" name="Entries" radius={[4, 4, 0, 0]} maxBarSize={isSingleLevel ? 80 : 48}>
              {data.map((entry) => (
                <Cell key={entry.name} fill={LEVEL_BAR_COLORS[entry.name] || "#6b7280"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

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
} from "recharts";

const MAX_LABEL_CHARS = 20;

function truncateLabel(value: string | number): string {
  const label = String(value);
  return label.length > MAX_LABEL_CHARS
    ? label.slice(0, MAX_LABEL_CHARS - 1) + "…"
    : label;
}

interface SourceChartProps {
  distribution: Record<string, number>;
}

export function SourceChart({ distribution }: SourceChartProps) {
  const data = Object.entries(distribution)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 12);

  if (data.length === 0) return null;

  const isSingleSource = data.length === 1;
  const maxDisplayLength = Math.max(...data.map((d) => Math.min(d.name.length, MAX_LABEL_CHARS)));
  const yAxisWidth = Math.min(Math.max(maxDisplayLength * 6.5, 60), 140);
  const chartHeight = isSingleSource ? 120 : Math.min(Math.max(data.length * 32 + 40, 160), 280);

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-sm font-semibold">Source Distribution</CardTitle>
            <CardDescription className="text-xs">
              {isSingleSource
                ? `All entries originate from a single source`
                : "Top components by entry count"
              }
            </CardDescription>
          </div>
          {isSingleSource && (
            <Badge variant="secondary" className="text-[10px] font-normal py-0">
              Single source
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="pt-2">
        <ResponsiveContainer width="100%" height={chartHeight}>
          <BarChart data={data} layout="vertical" margin={{ top: 8, right: 8, bottom: 4, left: 0 }}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="var(--color-border)"
              horizontal={false}
            />
            <XAxis
              type="number"
              fontSize={11}
              tick={{ fill: "var(--color-muted-foreground)" }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              dataKey="name"
              type="category"
              width={yAxisWidth}
              fontSize={11}
              tick={{ fill: "var(--color-muted-foreground)" }}
              tickFormatter={truncateLabel}
              axisLine={false}
              tickLine={false}
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
            <Bar dataKey="value" name="Entries" fill="var(--color-chart-1)" radius={[0, 4, 4, 0]} maxBarSize={28} />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

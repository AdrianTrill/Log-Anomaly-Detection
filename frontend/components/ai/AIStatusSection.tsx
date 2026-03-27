"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Brain, Cpu, AlertTriangle, ArrowRight } from "lucide-react";
import type { InferenceSummary } from "@/types/log";
import { formatModelName, formatAnomalyRate } from "@/lib/inference";

interface AIStatusSectionProps {
  totalEntries: number;
  analyzedCount: number;
  inferenceSummary: InferenceSummary | null;
}

export function AIStatusSection({ totalEntries, analyzedCount, inferenceSummary }: AIStatusSectionProps) {
  const isCompleted = inferenceSummary?.status === "completed" && analyzedCount > 0;
  const anomalyCount = inferenceSummary?.anomalies_detected ?? 0;
  const anomalyRate = formatAnomalyRate(anomalyCount, analyzedCount);
  const modelLabel = formatModelName(inferenceSummary?.model_name ?? null);

  return (
    <Card className={`border-border/50 bg-card/50 ${isCompleted ? "border-solid" : "border-dashed"}`}>
      <CardContent className="pt-5 pb-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className={`flex h-6 w-6 items-center justify-center rounded shrink-0 ${
              isCompleted ? "bg-emerald-500/15" : "bg-muted"
            }`}>
              <Brain className={`h-3.5 w-3.5 ${isCompleted ? "text-emerald-500" : "text-muted-foreground"}`} />
            </div>
            <div>
              <h2 className="text-sm font-semibold">Anomaly Detection</h2>
              <p className="text-[11px] text-muted-foreground/70">
                {isCompleted
                  ? `${anomalyCount} anomal${anomalyCount === 1 ? "y" : "ies"} in ${analyzedCount} entries (${anomalyRate}%)`
                  : `${totalEntries} entries ready for inspection`}
              </p>
            </div>
          </div>
          {isCompleted ? (
            <Badge variant="secondary" className="text-[9px] py-0 font-normal bg-emerald-500/15 text-emerald-600 dark:text-emerald-400">
              Complete
            </Badge>
          ) : (
            <Badge variant="outline" className="text-[9px] border-dashed text-muted-foreground/50 font-normal py-0">
              Parse Only
            </Badge>
          )}
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <div className="rounded-md bg-muted/25 border border-border/30 px-3 py-2">
            <p className="text-[9px] font-medium text-muted-foreground/50 uppercase tracking-widest mb-1">
              Model
            </p>
            <div className="flex items-center gap-1.5">
              <Cpu className={`h-3 w-3 ${isCompleted ? "text-foreground/70" : "text-muted-foreground/50"}`} />
              <span className="text-xs font-medium">{modelLabel}</span>
            </div>
          </div>

          <div className="rounded-md bg-muted/25 border border-border/30 px-3 py-2">
            <p className="text-[9px] font-medium text-muted-foreground/50 uppercase tracking-widest mb-1">
              Results
            </p>
            {isCompleted ? (
              <div className="flex items-center gap-2">
                {anomalyCount > 0 ? (
                  <Badge variant="secondary" className="text-[9px] py-0 bg-red-500/15 text-red-600 dark:text-red-400 font-normal">
                    <AlertTriangle className="h-2.5 w-2.5 mr-0.5" />
                    {anomalyCount} anomal{anomalyCount === 1 ? "y" : "ies"} ({anomalyRate}%)
                  </Badge>
                ) : (
                  <span className="text-[10px] text-emerald-600 dark:text-emerald-400">No anomalies detected</span>
                )}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground/50">No inference run</p>
            )}
          </div>
        </div>

        {!isCompleted && (
          <span className="text-[10px] text-muted-foreground/40 flex items-center gap-1">
            Load a benchmark dataset to run anomaly detection <ArrowRight className="h-2.5 w-2.5" />
          </span>
        )}
      </CardContent>
    </Card>
  );
}

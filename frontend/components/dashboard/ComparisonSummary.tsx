"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { AlertTriangle, CheckCircle2, GitCompareArrows } from "lucide-react";
import type { InferenceSummary } from "@/types/log";
import type { AgreementStats } from "@/lib/comparison";
import { shortModelLabel, columnModelLabel, formatAnomalyRate, formatThreshold } from "@/lib/inference";

interface ComparisonSummaryProps {
  summaryA: InferenceSummary | null;
  summaryB: InferenceSummary | null;
  agreement: AgreementStats;
  modelAId: string;
  modelBId: string;
}

function ModelCard({ summary, modelId }: { summary: InferenceSummary | null; modelId: string }) {
  const isCompleted = summary?.status === "completed";
  const anomalyCount = summary?.anomalies_detected ?? 0;
  const analyzed = summary?.entries_analyzed ?? 0;
  const anomalyRate = formatAnomalyRate(anomalyCount, analyzed);
  const label = shortModelLabel(modelId);

  return (
    <Card className="border-border/50 bg-card/50">
      <CardContent className="pt-3 pb-3 px-3.5 space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold">{label}</span>
          {summary?.threshold != null && (
            <Badge variant="outline" className="text-[9px] py-0 px-1.5 font-normal text-muted-foreground/70 border-border/40">
              Threshold {formatThreshold(summary.threshold)}
            </Badge>
          )}
        </div>

        {isCompleted ? (
          <div className="space-y-0.5">
            <div className="flex items-baseline gap-2">
              {anomalyCount > 0 ? (
                <>
                  <span className="text-lg font-bold tabular-nums text-red-600 dark:text-red-400">
                    {anomalyCount}
                  </span>
                  <span className="text-[11px] text-muted-foreground/60">
                    anomal{anomalyCount === 1 ? "y" : "ies"}
                  </span>
                </>
              ) : (
                <span className="text-[11px] text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  No anomalies detected
                </span>
              )}
            </div>
            {anomalyCount > 0 && (
              <div className="flex items-center gap-1 text-[11px] text-muted-foreground/70">
                <AlertTriangle className="h-2.5 w-2.5 text-red-500/60" />
                {anomalyRate}% anomaly rate
              </div>
            )}
            <p className="text-[10px] text-muted-foreground/50">{analyzed.toLocaleString()} entries analyzed</p>
          </div>
        ) : (
          <span className="text-[10px] text-muted-foreground/50">No inference</span>
        )}
      </CardContent>
    </Card>
  );
}

function AgreementCard({
  agreement,
  modelAId,
  modelBId,
}: {
  agreement: AgreementStats;
  modelAId: string;
  modelBId: string;
}) {
  const agreeCount = agreement.bothAnomaly + agreement.bothNormal;
  const disagreeCount = agreement.onlyA + agreement.onlyB;
  const agreeRate = agreement.total > 0 ? ((agreeCount / agreement.total) * 100).toFixed(1) : "0.0";
  const labelA = columnModelLabel(modelAId);
  const labelB = columnModelLabel(modelBId);

  return (
    <Card className="border-border/50 bg-card/50">
      <CardContent className="pt-3 pb-3 px-3.5 space-y-2">
        <div className="flex items-center gap-2">
          <div className="flex h-5 w-5 items-center justify-center rounded bg-primary/10 shrink-0">
            <GitCompareArrows className="h-3 w-3 text-primary" />
          </div>
          <span className="text-xs font-semibold">Agreement</span>
          <div className="flex items-center gap-1.5 ml-auto">
            {disagreeCount > 0 && (
              <Badge variant="outline" className="text-[9px] py-0 px-1.5 font-mono tabular-nums text-amber-600 dark:text-amber-400 border-amber-500/30">
                {disagreeCount} disagree
              </Badge>
            )}
            <Badge variant="outline" className="text-[9px] py-0 font-mono tabular-nums">
              {agreeRate}%
            </Badge>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-x-3 gap-y-1">
          <StatRow label="Both Anomaly" value={agreement.bothAnomaly} color="text-red-600 dark:text-red-400" />
          <StatRow label="Both Normal" value={agreement.bothNormal} color="text-emerald-600 dark:text-emerald-400" />
          <StatRow label={`Only ${labelA}`} value={agreement.onlyA} color="text-amber-600 dark:text-amber-400" />
          <StatRow label={`Only ${labelB}`} value={agreement.onlyB} color="text-amber-600 dark:text-amber-400" />
        </div>
      </CardContent>
    </Card>
  );
}

function StatRow({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-[10px] text-muted-foreground/60">{label}</span>
      <span className={`text-xs font-mono font-semibold tabular-nums ${color}`}>{value}</span>
    </div>
  );
}

export function ComparisonSummary({ summaryA, summaryB, agreement, modelAId, modelBId }: ComparisonSummaryProps) {
  return (
    <div className="grid gap-2.5 sm:grid-cols-3">
      <ModelCard summary={summaryA} modelId={modelAId} />
      <ModelCard summary={summaryB} modelId={modelBId} />
      <AgreementCard agreement={agreement} modelAId={modelAId} modelBId={modelBId} />
    </div>
  );
}

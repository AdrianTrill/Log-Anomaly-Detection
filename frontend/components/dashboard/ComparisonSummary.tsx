"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Info, GitCompareArrows } from "lucide-react";
import type { InferenceSummary } from "@/types/log";
import type { AgreementStats } from "@/lib/comparison";
import { shortModelLabel, columnModelLabel, formatThreshold } from "@/lib/inference";

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
  const normalCount = analyzed - anomalyCount;
  const anomalyRate = analyzed > 0 ? ((anomalyCount / analyzed) * 100).toFixed(1) : "0.0";
  const label = shortModelLabel(modelId);

  return (
    <Card className="border-border/50 bg-card/50">
      <CardContent className="pt-3 pb-3 px-3.5">
        <p className="text-xs font-semibold mb-2">{label}</p>

        {isCompleted ? (
          <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
            <Stat
              label="Anomalies"
              value={anomalyCount}
              color="text-red-600 dark:text-red-400"
              bold
            />
            <Stat
              label="Normal"
              value={normalCount}
              color="text-emerald-600 dark:text-emerald-400"
              bold
            />
            <Stat
              label="Anomaly rate"
              value={`${anomalyRate}%`}
              color="text-muted-foreground/70"
            />
            <Stat
              label="Threshold"
              value={formatThreshold(summary?.threshold)}
              color="text-muted-foreground/70"
            />
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
  const disagreeRate = agreement.total > 0 ? ((disagreeCount / agreement.total) * 100).toFixed(1) : "0.0";
  const colA = columnModelLabel(modelAId);
  const colB = columnModelLabel(modelBId);

  let interpretation = "Both models make the same decisions on this slice.";
  if (agreement.onlyA > agreement.onlyB) {
    interpretation = "Only Transformer Encoder flags anomalies in this slice.";
  } else if (agreement.onlyB > agreement.onlyA) {
    interpretation = "Only LogBERT flags anomalies in this slice.";
  } else if (disagreeCount > 0) {
    interpretation = `Each model uniquely flags ${agreement.onlyA} entries.`;
  }

  return (
    <Card className="border-border/50 bg-card/50">
      <CardContent className="pt-3 pb-3 px-3.5">
        <div className="flex items-center gap-2 mb-0.5">
          <div className="flex h-5 w-5 items-center justify-center rounded bg-primary/10 shrink-0">
            <GitCompareArrows className="h-3 w-3 text-primary" />
          </div>
          <span className="text-xs font-semibold">Agreement</span>
        </div>
        <p className="text-[10px] text-muted-foreground/40 mb-2">How the two models classify this slice</p>

        <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 mb-2">
          <Stat label="Agreement" value={`${agreeRate}%`} color="text-emerald-600 dark:text-emerald-400" />
          <Stat label="Disagreement" value={`${disagreeRate}%`} color="text-amber-600 dark:text-amber-400" />
        </div>

        <div className="grid grid-cols-2 gap-x-4 gap-y-1 pt-1.5 border-t border-border/20">
          <StatRow label="Flagged by both" value={agreement.bothAnomaly} color="text-red-600 dark:text-red-400" />
          <StatRow label="Normal by both" value={agreement.bothNormal} color="text-emerald-600 dark:text-emerald-400" />
          <StatRow label={`Only ${colA}`} value={agreement.onlyA} color="text-amber-600 dark:text-amber-400" />
          <StatRow label={`Only ${colB}`} value={agreement.onlyB} color="text-amber-600 dark:text-amber-400" />
        </div>

        <p className="text-[10px] text-muted-foreground/50 italic mt-2">{interpretation}</p>
      </CardContent>
    </Card>
  );
}

function Stat({
  label,
  value,
  color,
  bold,
}: {
  label: string;
  value: string | number;
  color: string;
  bold?: boolean;
}) {
  return (
    <div>
      <p className="text-[10px] text-muted-foreground/50 leading-none mb-0.5">{label}</p>
      <p className={`text-xs font-mono tabular-nums leading-none ${color} ${bold ? "font-semibold" : "font-medium"}`}>
        {value}
      </p>
    </div>
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
    <div className="space-y-1.5">
      <div className="grid gap-2.5 sm:grid-cols-3 items-stretch">
        <ModelCard summary={summaryA} modelId={modelAId} />
        <ModelCard summary={summaryB} modelId={modelBId} />
        <AgreementCard agreement={agreement} modelAId={modelAId} modelBId={modelBId} />
      </div>
      <div className="flex items-center gap-1.5 px-0.5">
        <Info className="h-3 w-3 text-muted-foreground/30 shrink-0" />
        <p className="text-[10px] text-muted-foreground/40">
          Counts are per entry in the selected slice. An entry is anomalous when its score exceeds the dataset threshold.
        </p>
      </div>
    </div>
  );
}

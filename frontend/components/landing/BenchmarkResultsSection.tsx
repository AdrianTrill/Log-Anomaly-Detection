"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { BENCHMARK_RESULTS } from "@/lib/benchmark-results";
import type { BenchmarkResultSummary } from "@/lib/benchmark-results";

function ResultCard({ r }: { r: BenchmarkResultSummary }) {
  return (
    <Card className="border-border/40 bg-card/40">
      <CardContent className="pt-3 pb-3 px-3.5 flex flex-col">
        {/* Header */}
        <div className="flex items-center gap-1.5 mb-2.5">
          <Badge
            variant="outline"
            className="text-[8px] py-0 px-1.5 font-normal text-muted-foreground/60 border-border/35"
          >
            {r.dataset}
          </Badge>
          <span className="text-[11px] font-semibold">{r.modelLabel}</span>
        </div>

        {/* F1 hero */}
        <div className="flex items-baseline gap-1.5 mb-3">
          <span className="text-lg font-bold tabular-nums leading-none">{r.f1.toFixed(2)}%</span>
          <span className="text-[10px] text-muted-foreground/55">F1</span>
        </div>

        {/* Secondary metrics */}
        <div className="grid grid-cols-2 gap-x-4 gap-y-2 pb-2.5 border-b border-border/20">
          <Metric label="Precision" value={`${r.precision.toFixed(2)}%`} />
          <Metric label="Recall" value={`${r.recall.toFixed(2)}%`} />
          <Metric label="ROC-AUC" value={`${r.rocAuc.toFixed(2)}%`} />
          <Metric label="Threshold" value={r.threshold.toFixed(2)} />
        </div>

        {/* Confusion mini-grid */}
        <div className="grid grid-cols-2 gap-x-4 gap-y-1 pt-2.5 mt-auto">
          <CmCell label="TP" value={r.tp} />
          <CmCell label="FP" value={r.fp} />
          <CmCell label="FN" value={r.fn} />
          <CmCell label="TN" value={r.tn} />
        </div>
      </CardContent>
    </Card>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[9px] text-muted-foreground/50 leading-none mb-0.5">{label}</p>
      <p className="text-[11px] font-mono font-medium tabular-nums text-muted-foreground/80 leading-none">{value}</p>
    </div>
  );
}

function CmCell({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-[8px] font-mono text-muted-foreground/35 w-3 text-right">{label}</span>
      <span className="text-[9px] font-mono tabular-nums text-muted-foreground/45">{value.toLocaleString()}</span>
    </div>
  );
}

export function BenchmarkResultsSection() {
  return (
    <div className="space-y-1.5">
      <p className="text-[10px] font-semibold text-muted-foreground/60 uppercase tracking-wider px-1">
        Offline Benchmark Results
      </p>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {BENCHMARK_RESULTS.map((r) => (
          <ResultCard key={r.id} r={r} />
        ))}
      </div>
    </div>
  );
}

"use client";

import { useRef, useEffect } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { X, Brain, FileText, SplitSquareVertical, Sparkles } from "lucide-react";
import type { ComparisonEntry } from "@/types/log";
import { LOG_LEVEL_COLORS } from "@/types/log";
import {
  shortModelLabel,
  formatScore,
  formatThreshold,
  ANOMALY_COLORS,
  NORMAL_COLORS,
  PREDICTION_LABEL,
  getScopeContext,
  getDefaultThreshold,
} from "@/lib/inference";

interface ComparisonDetailPanelProps {
  entry: ComparisonEntry;
  onClose: () => void;
  thresholdA?: number | null;
  thresholdB?: number | null;
}

function FieldCard({ label, value, mono }: { label: string; value: React.ReactNode; mono?: boolean }) {
  return (
    <div className="space-y-0.5">
      <p className="text-[9px] font-medium text-muted-foreground uppercase tracking-widest">{label}</p>
      <div className={`text-xs leading-snug ${mono ? "font-mono" : ""}`}>
        {value || <span className="text-muted-foreground/50">&mdash;</span>}
      </div>
    </div>
  );
}

function ScoreBar({ score, threshold, prediction }: { score: number; threshold: number; prediction: string | null }) {
  const isAnomaly = prediction === "anomaly";
  const pct = Math.min(score * 100, 100);
  const thresholdPct = Math.min(threshold * 100, 100);

  return (
    <div className="mb-2">
      <div className="flex items-center justify-between mb-1">
        <span className="text-[9px] font-medium text-muted-foreground/50 uppercase tracking-widest">
          Score vs Threshold
        </span>
        <span className={`text-[10px] font-mono font-medium ${isAnomaly ? ANOMALY_COLORS.text : NORMAL_COLORS.text}`}>
          {formatScore(score)}% / {formatScore(threshold)}%
        </span>
      </div>
      <div className="relative h-2 rounded-full bg-muted/50 border border-border/30 overflow-hidden">
        <div
          className={`absolute inset-y-0 left-0 rounded-full transition-all ${
            isAnomaly ? "bg-red-500/70" : "bg-emerald-500/70"
          }`}
          style={{ width: `${pct}%` }}
        />
        <div
          className="absolute inset-y-0 w-px bg-foreground/40"
          style={{ left: `${thresholdPct}%` }}
        />
      </div>
    </div>
  );
}

function PredictionBadge({ prediction }: { prediction: string }) {
  const colors = prediction === "anomaly" ? ANOMALY_COLORS : NORMAL_COLORS;
  const label = PREDICTION_LABEL[prediction] ?? prediction;
  return (
    <Badge variant="secondary" className={`text-[10px] py-0 font-medium ${colors.badge}`}>
      {label}
    </Badge>
  );
}

function ModelAnalysisColumn({
  modelName,
  score,
  prediction,
  threshold,
}: {
  modelName: string;
  score: number | null;
  prediction: string | null;
  threshold: number | null;
}) {
  const resolvedThreshold = threshold ?? getDefaultThreshold(modelName);
  const label = shortModelLabel(modelName);

  return (
    <div className="flex-1 space-y-2">
      <p className="text-[10px] font-semibold text-muted-foreground/70 uppercase tracking-widest">{label}</p>

      {score !== null && resolvedThreshold !== null && (
        <ScoreBar score={score} threshold={resolvedThreshold} prediction={prediction} />
      )}

      <div className="grid grid-cols-2 gap-2">
        <FieldCard
          label="Score"
          value={
            score !== null ? (
              <span className={`text-xs font-mono font-medium ${prediction === "anomaly" ? ANOMALY_COLORS.text : NORMAL_COLORS.text}`}>
                {formatScore(score)}%
              </span>
            ) : null
          }
        />
        <FieldCard
          label="Prediction"
          value={prediction ? <PredictionBadge prediction={prediction} /> : null}
        />
        <FieldCard
          label="Threshold"
          value={
            resolvedThreshold !== null ? (
              <span className="text-xs font-mono">{formatThreshold(resolvedThreshold)}</span>
            ) : null
          }
        />
      </div>
    </div>
  );
}

export function ComparisonDetailPanel({
  entry,
  onClose,
  thresholdA,
  thresholdB,
}: ComparisonDetailPanelProps) {
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    panelRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [entry.base.line_number]);

  const base = entry.base;
  const levelColor = base.level ? LOG_LEVEL_COLORS[base.level] || "" : "";
  const scopeContext = getScopeContext(entry.modelA.model_name);
  const disagree = entry.modelA.prediction !== entry.modelB.prediction;

  return (
    <div
      ref={panelRef}
      className="rounded-lg border border-primary/20 bg-card shadow-sm animate-in fade-in slide-in-from-top-2 duration-200"
    >
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-border/50 bg-muted/30">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-muted-foreground">Entry</span>
          <span className="font-mono text-xs font-semibold">#{base.line_number}</span>
          {base.level && (
            <Badge variant="outline" className={`${levelColor} text-[10px] py-0`}>
              {base.level}
            </Badge>
          )}
          {disagree && (
            <Badge variant="secondary" className="text-[9px] py-0 bg-amber-500/15 text-amber-600 dark:text-amber-400">
              Disagree
            </Badge>
          )}
        </div>
        <Button
          variant="ghost"
          size="icon"
          onClick={onClose}
          className="h-6 w-6 text-muted-foreground hover:text-foreground"
        >
          <X className="h-3.5 w-3.5" />
        </Button>
      </div>

      <div className="p-4 space-y-3.5">
        {/* Original Entry */}
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <div className="flex h-5 w-5 items-center justify-center rounded bg-muted shrink-0">
              <FileText className="h-3 w-3 text-muted-foreground" />
            </div>
            <h3 className="text-xs font-semibold">Original Entry</h3>
          </div>
          <pre className="whitespace-pre-wrap break-all font-mono text-[11px] leading-relaxed bg-muted/40 border border-border/40 p-2.5 rounded-md text-foreground/90">
            {base.raw_line}
          </pre>
        </div>

        <Separator className="opacity-50" />

        {/* Extracted Fields */}
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <div className="flex h-5 w-5 items-center justify-center rounded bg-muted shrink-0">
              <SplitSquareVertical className="h-3 w-3 text-muted-foreground" />
            </div>
            <h3 className="text-xs font-semibold">Extracted Fields</h3>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <FieldCard label="Timestamp" value={base.timestamp} mono />
            <FieldCard label="Level" value={
              base.level ? (
                <Badge variant="outline" className={`${levelColor} text-[10px] py-0`}>{base.level}</Badge>
              ) : null
            } />
            <FieldCard label="Source" value={base.source} mono />
          </div>
          {base.message && (
            <div className="mt-3">
              <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-widest mb-1">Parsed Message</p>
              <p className="text-[13px] leading-relaxed">{base.message}</p>
            </div>
          )}
        </div>

        {/* Normalized Pattern */}
        {base.normalized_message && (() => {
          const wasNormalized = base.normalized_message !== base.message;
          return (
            <>
              <Separator className="opacity-50" />
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-2">
                    <div className="flex h-5 w-5 items-center justify-center rounded bg-muted shrink-0">
                      <Sparkles className="h-3 w-3 text-muted-foreground" />
                    </div>
                    <h3 className="text-xs font-semibold">Normalized Pattern</h3>
                  </div>
                  <Badge
                    variant="secondary"
                    className={`text-[9px] py-0 font-normal ${
                      wasNormalized ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400" : ""
                    }`}
                  >
                    {wasNormalized ? "Normalization applied" : "No changes"}
                  </Badge>
                </div>
                <code className="text-[11px] font-mono bg-muted/40 border border-border/40 px-3 py-2.5 rounded-md break-all block leading-relaxed text-foreground/90">
                  {base.normalized_message}
                </code>
              </div>
            </>
          );
        })()}

        <Separator className="opacity-50" />

        {/* Side-by-side AI Analysis */}
        <div>
          <div className="flex items-center gap-2 mb-2.5">
            <div className="flex h-5 w-5 items-center justify-center rounded bg-primary/10 shrink-0">
              <Brain className="h-3 w-3 text-primary" />
            </div>
            <h3 className="text-xs font-semibold">AI Analysis</h3>
          </div>

          <div className="grid grid-cols-2 gap-4 rounded-md border border-border/50 bg-muted/25 p-4">
            <ModelAnalysisColumn
              modelName={entry.modelA.model_name}
              score={entry.modelA.anomaly_score}
              prediction={entry.modelA.prediction}
              threshold={thresholdA ?? null}
            />
            <div className="border-l border-border/30 pl-4">
              <ModelAnalysisColumn
                modelName={entry.modelB.model_name}
                score={entry.modelB.anomaly_score}
                prediction={entry.modelB.prediction}
                threshold={thresholdB ?? null}
              />
            </div>
          </div>

          {scopeContext && (
            <p className="text-[10px] text-muted-foreground/50 mt-2.5 leading-relaxed">
              {scopeContext}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

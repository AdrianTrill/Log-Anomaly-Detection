"use client";

import { useState, useRef, useEffect } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { X, Copy, Check, Brain, FileText, SplitSquareVertical, Sparkles } from "lucide-react";
import type { LogEntry } from "@/types/log";
import { LOG_LEVEL_COLORS } from "@/types/log";
import {
  formatModelName,
  formatScore,
  INFERENCE_STATUS_LABEL,
  PREDICTION_LABEL,
  ANOMALY_COLORS,
  NORMAL_COLORS,
  getScopeContext,
  getDefaultThreshold,
  formatThreshold,
} from "@/lib/inference";

interface LogDetailPanelProps {
  entry: LogEntry;
  onClose: () => void;
  threshold?: number | null;
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async (e: React.MouseEvent) => {
    e.stopPropagation();
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={handleCopy}
      className="h-5 w-5 text-muted-foreground/50 hover:text-foreground shrink-0"
    >
      {copied ? <Check className="h-3 w-3 text-emerald-500" /> : <Copy className="h-3 w-3" />}
    </Button>
  );
}

function StageHeader({
  icon: Icon,
  title,
  description,
  badge,
}: {
  icon: React.ElementType;
  title: string;
  description: string;
  badge?: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between mb-2.5">
      <div className="flex items-start gap-2">
        <div className="flex h-5 w-5 items-center justify-center rounded bg-muted mt-0.5 shrink-0">
          <Icon className="h-3 w-3 text-muted-foreground" />
        </div>
        <div>
          <h3 className="text-xs font-semibold">{title}</h3>
          <p className="text-[10px] text-muted-foreground leading-relaxed">{description}</p>
        </div>
      </div>
      {badge}
    </div>
  );
}

export function LogDetailPanel({ entry, onClose, threshold: externalThreshold }: LogDetailPanelProps) {
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    panelRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [entry.line_number]);

  const levelColor = entry.level ? LOG_LEVEL_COLORS[entry.level] || "" : "";
  const showParseStatus = entry.parse_status !== "parsed";
  const isCompleted = entry.inference_status === "completed";
  const resolvedThreshold = externalThreshold ?? getDefaultThreshold(entry.model_name);
  const scopeContext = getScopeContext(entry.model_name);

  return (
    <div
      ref={panelRef}
      className="rounded-lg border border-primary/20 bg-card shadow-sm animate-in fade-in slide-in-from-top-2 duration-200"
    >
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-border/50 bg-muted/30">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-muted-foreground">Entry</span>
          <span className="font-mono text-xs font-semibold">#{entry.line_number}</span>
          {entry.level && (
            <Badge variant="outline" className={`${levelColor} text-[10px] py-0`}>
              {entry.level}
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

      <div className="p-4 space-y-5">
        {/* Stage 1: Original Entry */}
        <div>
          <StageHeader
            icon={FileText}
            title="Original Entry"
            description="Raw log line from source"
          />
          <div className="relative group">
            <pre className="whitespace-pre-wrap break-all font-mono text-[11px] leading-relaxed bg-muted/40 border border-border/40 p-3 rounded-md text-foreground/90">
              {entry.raw_line}
            </pre>
            <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
              <CopyButton text={entry.raw_line} />
            </div>
          </div>
        </div>

        <Separator className="opacity-50" />

        {/* Stage 2: Extracted Fields */}
        <div>
          <StageHeader
            icon={SplitSquareVertical}
            title="Extracted Fields"
            description="Structured fields parsed from the raw line"
          />
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <FieldCard label="Timestamp" value={entry.timestamp} mono />
            <FieldCard label="Level" value={
              entry.level ? (
                <Badge variant="outline" className={`${levelColor} text-[10px] py-0`}>
                  {entry.level}
                </Badge>
              ) : null
            } />
            <FieldCard label="Source" value={entry.source} mono />
            {showParseStatus && (
              <FieldCard label="Parse Status" value={
                <Badge variant="secondary" className="text-[10px] py-0 text-amber-600 dark:text-amber-400 bg-amber-500/15">
                  {entry.parse_status}
                </Badge>
              } />
            )}
          </div>
          {entry.message && (
            <div className="mt-3">
              <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-widest mb-1">
                Parsed Message
              </p>
              <p className="text-[13px] leading-relaxed">{entry.message}</p>
            </div>
          )}
        </div>

        {/* Stage 3: Normalized Pattern */}
        {entry.normalized_message && (() => {
          const wasNormalized = entry.normalized_message !== entry.message;
          return (
            <>
              <Separator className="opacity-50" />
              <div>
                <StageHeader
                  icon={Sparkles}
                  title="Normalized Event Pattern"
                  description="Variable values replaced with tokens for ML"
                  badge={
                    <Badge
                      variant="secondary"
                      className={`text-[9px] py-0 font-normal ${
                        wasNormalized
                          ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400"
                          : ""
                      }`}
                    >
                      {wasNormalized ? "Normalization applied" : "No changes"}
                    </Badge>
                  }
                />
                <div className="relative group">
                  <code className="text-[11px] font-mono bg-muted/40 border border-border/40 px-3 py-2.5 rounded-md break-all block leading-relaxed text-foreground/90">
                    {entry.normalized_message}
                  </code>
                  <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <CopyButton text={entry.normalized_message} />
                  </div>
                </div>
              </div>
            </>
          );
        })()}

        <Separator className="opacity-50" />

        {/* Stage 4: AI Analysis */}
        <div>
          <StageHeader
            icon={Brain}
            title="AI Analysis"
            description="Anomaly detection inference"
            badge={<InferenceStatusBadge status={entry.inference_status} />}
          />

          {isCompleted && entry.anomaly_score !== null && resolvedThreshold !== null && (
            <ScoreBar
              score={entry.anomaly_score}
              threshold={resolvedThreshold}
              prediction={entry.prediction}
            />
          )}

          <div className={`rounded-md border p-3 grid grid-cols-2 sm:grid-cols-4 gap-3 ${
            isCompleted
              ? "border-border/50 bg-muted/25"
              : "border-dashed border-border/50 bg-muted/15"
          }`}>
            <FieldCard label="Model" value={formatModelName(entry.model_name)} />
            <FieldCard label="Anomaly Score" value={
              entry.anomaly_score !== null ? <ScoreBadge score={entry.anomaly_score} prediction={entry.prediction} /> : null
            } />
            <FieldCard label="Prediction" value={
              entry.prediction ? <PredictionBadge prediction={entry.prediction} /> : null
            } />
            <FieldCard label="Threshold" value={
              resolvedThreshold !== null
                ? <span className="text-xs font-mono">{formatThreshold(resolvedThreshold)}</span>
                : null
            } />
          </div>

          {isCompleted && scopeContext && (
            <p className="text-[10px] text-muted-foreground/50 mt-2.5 leading-relaxed">
              {scopeContext}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

function ScoreBar({
  score,
  threshold,
  prediction,
}: {
  score: number;
  threshold: number;
  prediction: string | null;
}) {
  const isAnomaly = prediction === "anomaly";
  const pct = Math.min(score * 100, 100);
  const thresholdPct = Math.min(threshold * 100, 100);

  return (
    <div className="mb-3">
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

function InferenceStatusBadge({ status }: { status: string }) {
  const label = INFERENCE_STATUS_LABEL[status] ?? "Pending";
  const isComplete = status === "completed";
  return (
    <Badge
      variant="secondary"
      className={`text-[9px] font-normal py-0 ${isComplete ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400" : ""}`}
    >
      {label}
    </Badge>
  );
}

function ScoreBadge({ score, prediction }: { score: number; prediction: string | null }) {
  const colors = prediction === "anomaly" ? ANOMALY_COLORS : NORMAL_COLORS;
  return (
    <span className={`text-xs font-mono font-medium ${colors.text}`}>
      {formatScore(score)}%
    </span>
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

function FieldCard({
  label,
  value,
  mono,
}: {
  label: string;
  value: React.ReactNode;
  mono?: boolean;
}) {
  return (
    <div className="space-y-0.5">
      <p className="text-[9px] font-medium text-muted-foreground uppercase tracking-widest">
        {label}
      </p>
      <div className={`text-xs leading-snug ${mono ? "font-mono" : ""}`}>
        {value || <span className="text-muted-foreground/50">&mdash;</span>}
      </div>
    </div>
  );
}

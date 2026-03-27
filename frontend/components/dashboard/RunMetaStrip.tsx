"use client";

import { Badge } from "@/components/ui/badge";
import type { RunContext, InferenceSummary, ComparisonContext } from "@/types/log";
import { formatModelName, shortModelLabel, getScopeLabel, formatThreshold } from "@/lib/inference";

interface RunMetaStripProps {
  context: RunContext;
  inferenceSummary: InferenceSummary | null;
  comparisonContext?: ComparisonContext;
  inferenceSummaryB?: InferenceSummary | null;
}

function MetaItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-[9px] font-medium text-muted-foreground/50 uppercase tracking-widest">
        {label}
      </span>
      <span className="text-[12px] font-medium text-foreground/80">{value}</span>
    </div>
  );
}

function Divider() {
  return <span className="text-muted-foreground/15 select-none">·</span>;
}

export function RunMetaStrip({
  context,
  inferenceSummary,
  comparisonContext,
  inferenceSummaryB,
}: RunMetaStripProps) {
  const endLine = context.startLine + context.lineCount - 1;
  const lineRange =
    context.startLine === 1
      ? `1\u2013${endLine.toLocaleString()}`
      : `${context.startLine.toLocaleString()}\u2013${endLine.toLocaleString()}`;

  const isComparison = !!comparisonContext;
  const threshold = inferenceSummary?.threshold ?? null;
  const scope = inferenceSummary?.scope ?? null;

  const thresholdB = inferenceSummaryB?.threshold ?? null;
  const thresholdsSame = threshold != null && thresholdB != null && threshold === thresholdB;

  let modelDisplay: string;
  if (isComparison) {
    const labelA = shortModelLabel(comparisonContext.modelAId);
    const labelB = shortModelLabel(comparisonContext.modelBId);
    modelDisplay = `${labelA} vs ${labelB}`;
  } else {
    modelDisplay = formatModelName(inferenceSummary?.model_name ?? context.modelId);
  }

  let thresholdDisplay: string;
  if (isComparison) {
    if (thresholdsSame && threshold != null) {
      thresholdDisplay = formatThreshold(threshold);
    } else if (threshold != null && thresholdB != null) {
      thresholdDisplay = `${formatThreshold(threshold)} / ${formatThreshold(thresholdB)}`;
    } else {
      thresholdDisplay = formatThreshold(threshold);
    }
  } else {
    thresholdDisplay = formatThreshold(threshold);
  }

  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 rounded-lg border border-border/30 bg-muted/20 px-3.5 py-2">
      <Badge variant="outline" className="text-[9px] py-0 px-1.5 font-semibold border-primary/30 text-primary/80">
        {context.datasetLabel}
      </Badge>
      <MetaItem label={isComparison ? "Models" : "Model"} value={modelDisplay} />
      <Divider />
      {scope && <><MetaItem label="Scope" value={getScopeLabel(scope)} /><Divider /></>}
      {thresholdDisplay !== "\u2014" && <><MetaItem label="Threshold" value={thresholdDisplay} /><Divider /></>}
      <MetaItem label="Sample" value={context.presetLabel} />
      <Divider />
      <MetaItem label="Lines" value={`${lineRange} (${context.lineCount.toLocaleString()})`} />
    </div>
  );
}

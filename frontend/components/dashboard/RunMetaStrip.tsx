"use client";

import { Badge } from "@/components/ui/badge";
import type { RunContext, InferenceSummary } from "@/types/log";
import { formatModelName, getScopeLabel, formatThreshold } from "@/lib/inference";

interface RunMetaStripProps {
  context: RunContext;
  inferenceSummary: InferenceSummary | null;
}

function MetaItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-[9px] font-medium text-muted-foreground/50 uppercase tracking-widest">
        {label}
      </span>
      <span className="text-[11px] font-medium text-foreground/80">{value}</span>
    </div>
  );
}

export function RunMetaStrip({ context, inferenceSummary }: RunMetaStripProps) {
  const endLine = context.startLine + context.lineCount - 1;
  const lineRange =
    context.startLine === 1
      ? `1\u2013${endLine.toLocaleString()}`
      : `${context.startLine.toLocaleString()}\u2013${endLine.toLocaleString()}`;

  const threshold = inferenceSummary?.threshold ?? null;
  const scope = inferenceSummary?.scope ?? null;
  const modelLabel = formatModelName(inferenceSummary?.model_name ?? context.modelId);

  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 rounded-lg border border-border/30 bg-muted/20 px-4 py-2.5">
      <Badge variant="outline" className="text-[9px] py-0 px-1.5 font-semibold border-primary/30 text-primary/80">
        {context.datasetLabel}
      </Badge>
      <MetaItem label="Model" value={modelLabel} />
      {scope && <MetaItem label="Scope" value={getScopeLabel(scope)} />}
      {threshold != null && <MetaItem label="Threshold" value={formatThreshold(threshold)} />}
      <MetaItem label="Sample" value={context.presetLabel} />
      <MetaItem label="Lines" value={lineRange} />
      <MetaItem label="Count" value={`${context.lineCount.toLocaleString()} lines`} />
    </div>
  );
}

"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Brain, Cpu, CircleDashed, Play, ArrowRight } from "lucide-react";

interface AIStatusSectionProps {
  totalEntries: number;
  analyzedCount: number;
}

export function AIStatusSection({ totalEntries, analyzedCount }: AIStatusSectionProps) {
  const isConnected = analyzedCount > 0;

  return (
    <Card className="border-dashed border-border/50 bg-card/50">
      <CardContent className="pt-5 pb-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="flex h-6 w-6 items-center justify-center rounded bg-muted text-muted-foreground shrink-0">
              <Brain className="h-3.5 w-3.5" />
            </div>
            <div>
              <div className="flex items-baseline gap-2">
                <h2 className="text-sm font-semibold">Anomaly Detection</h2>
                <span className="text-[9px] text-muted-foreground/40 uppercase tracking-widest font-medium">4</span>
              </div>
              <p className="text-[11px] text-muted-foreground/70">
                {isConnected
                  ? `${analyzedCount} of ${totalEntries} entries analyzed`
                  : `${totalEntries} entries parsed and ready for model inference`}
              </p>
            </div>
          </div>
          <Badge variant="outline" className="text-[9px] border-dashed text-muted-foreground/50 font-normal py-0">
            Next Step
          </Badge>
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          <div className="rounded-md bg-muted/25 border border-border/30 px-3 py-2">
            <p className="text-[9px] font-medium text-muted-foreground/50 uppercase tracking-widest mb-1">
              Model
            </p>
            <div className="flex items-center gap-1.5">
              <Cpu className="h-3 w-3 text-muted-foreground/50" />
              <span className="text-xs font-medium">Transformer Encoder</span>
            </div>
          </div>

          <div className="rounded-md bg-muted/25 border border-border/30 px-3 py-2">
            <p className="text-[9px] font-medium text-muted-foreground/50 uppercase tracking-widest mb-1">
              Connection
            </p>
            <div className="flex items-center gap-1.5">
              <CircleDashed className={`h-3 w-3 ${isConnected ? "text-emerald-500" : "text-muted-foreground/30"}`} />
              <span className="text-xs">
                {isConnected ? "Connected" : "Awaiting model"}
              </span>
            </div>
          </div>

          <div className="rounded-md bg-muted/25 border border-border/30 px-3 py-2">
            <p className="text-[9px] font-medium text-muted-foreground/50 uppercase tracking-widest mb-1">
              Results
            </p>
            <p className="text-xs">
              {isConnected
                ? `${analyzedCount} / ${totalEntries}`
                : "No results yet"}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 pt-0.5">
          <Button disabled variant="outline" size="sm" className="gap-1.5 text-[11px] h-7">
            <Play className="h-3 w-3" />
            Run Anomaly Detection
          </Button>
          {!isConnected && (
            <span className="text-[10px] text-muted-foreground/40 flex items-center gap-1">
              Logs are parsed and ready <ArrowRight className="h-2.5 w-2.5" /> connect a model to begin
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

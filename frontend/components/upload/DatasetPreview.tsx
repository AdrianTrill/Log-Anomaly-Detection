"use client";

import { useState, useEffect } from "react";
import { Loader2, AlertCircle, Play, Zap, BarChart3, Layers } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { fetchDatasets, previewDataset } from "@/lib/api";
import type { DatasetInfo, UploadResponse } from "@/types/log";

// ── Demo presets per dataset ──
// HDFS: first-N is fine (anomalies are distributed evenly across blocks).
// BGL: curated slices from anomaly-rich regions — the start of the file
//      contains almost exclusively normal lines which makes a weak demo.
//      Each start_line was chosen from scanning BGL.log for mixed
//      normal/anomalous regions (~30-50% anomaly density).

interface PresetConfig {
  id: string;
  label: string;
  lines: number;
  startLine: number;
  icon: typeof Zap;
}

const PRESETS: Record<string, PresetConfig[]> = {
  HDFS_v1: [
    { id: "quick",    label: "Quick",    lines: 200,  startLine: 1, icon: Zap },
    { id: "standard", label: "Standard", lines: 1000, startLine: 1, icon: BarChart3 },
    { id: "extended", label: "Extended", lines: 5000, startLine: 1, icon: Layers },
  ],
  BGL: [
    { id: "quick",    label: "Quick",    lines: 200,  startLine: 75051,  icon: Zap },
    { id: "standard", label: "Standard", lines: 1000, startLine: 14001,  icon: BarChart3 },
    { id: "extended", label: "Extended", lines: 5000, startLine: 75001,  icon: Layers },
  ],
};

const DEFAULT_PRESETS: PresetConfig[] = [
  { id: "quick",    label: "Quick",    lines: 200,  startLine: 1, icon: Zap },
  { id: "standard", label: "Standard", lines: 1000, startLine: 1, icon: BarChart3 },
  { id: "extended", label: "Extended", lines: 5000, startLine: 1, icon: Layers },
];

const DATASET_META: Record<string, { label: string; tag: string; desc: string }> = {
  HDFS_v1: {
    label: "HDFS",
    tag: "Block-session",
    desc: "Hadoop distributed file system logs — anomaly detection per block session",
  },
  BGL: {
    label: "BGL",
    tag: "Sliding-window",
    desc: "Blue Gene/L supercomputer logs — anomaly detection per sliding window",
  },
};

interface DatasetPreviewProps {
  onResult: (data: UploadResponse) => void;
  disabled: boolean;
}

export function DatasetPreview({ onResult, disabled }: DatasetPreviewProps) {
  const [datasets, setDatasets] = useState<DatasetInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState("");
  const [selectedDataset, setSelectedDataset] = useState("");
  const [selectedPreset, setSelectedPreset] = useState("standard");
  const [previewing, setPreviewing] = useState(false);
  const [previewError, setPreviewError] = useState("");

  useEffect(() => {
    fetchDatasets()
      .then((res) => {
        setDatasets(res.datasets);
        if (res.datasets.length > 0) {
          setSelectedDataset(res.datasets[0].name);
        }
      })
      .catch((err) => {
        setFetchError(err instanceof Error ? err.message : "Failed to load datasets");
      })
      .finally(() => setLoading(false));
  }, []);

  const presets = PRESETS[selectedDataset] ?? DEFAULT_PRESETS;
  const preset = presets.find((p) => p.id === selectedPreset) ?? presets[1];
  const isCurated = preset.startLine > 1;

  const handleRun = async () => {
    if (!selectedDataset) return;
    setPreviewing(true);
    setPreviewError("");
    try {
      const result = await previewDataset({
        dataset_name: selectedDataset,
        max_lines: preset.lines,
        ...(preset.startLine > 1 ? { start_line: preset.startLine } : {}),
      });
      onResult(result);
    } catch (err) {
      setPreviewError(err instanceof Error ? err.message : "Preview failed");
    } finally {
      setPreviewing(false);
    }
  };

  const meta = DATASET_META[selectedDataset];
  const dsLabel = meta?.label ?? selectedDataset;

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-xs text-muted-foreground py-6 justify-center">
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
        Loading datasets...
      </div>
    );
  }

  if (fetchError) {
    return (
      <div className="flex items-start gap-2 text-xs py-3">
        <AlertCircle className="h-3.5 w-3.5 text-destructive shrink-0 mt-0.5" />
        <span className="text-muted-foreground">{fetchError}</span>
      </div>
    );
  }

  if (datasets.length === 0) {
    return (
      <p className="text-xs text-muted-foreground py-3">
        No datasets found. Place log files in <code className="text-[10px] bg-muted px-1 py-0.5 rounded">datasets/raw/</code>.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      {/* Dataset selector */}
      <div className="space-y-1.5">
        <p className="text-[10px] font-medium text-muted-foreground/60 uppercase tracking-wider">Dataset</p>
        <div className="grid grid-cols-2 gap-2">
          {datasets.map((d) => {
            const m = DATASET_META[d.name];
            const isSelected = d.name === selectedDataset;
            return (
              <button
                key={d.name}
                onClick={() => { setSelectedDataset(d.name); setSelectedPreset("standard"); }}
                disabled={disabled || previewing}
                className={cn(
                  "relative rounded-lg border px-3.5 py-2.5 text-left transition-all",
                  isSelected
                    ? "border-primary/50 bg-primary/5 ring-1 ring-primary/20"
                    : "border-border/40 bg-card/50 hover:border-border/70 hover:bg-muted/30"
                )}
              >
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="text-sm font-semibold">{m?.label ?? d.name}</span>
                  {m && (
                    <Badge variant="outline" className="text-[8px] py-0 px-1.5 font-normal text-muted-foreground/60">
                      {m.tag}
                    </Badge>
                  )}
                </div>
                <p className="text-[10px] text-muted-foreground/50 leading-relaxed line-clamp-2">
                  {m?.desc ?? d.description}
                </p>
              </button>
            );
          })}
        </div>
      </div>

      {/* Preset selector */}
      <div className="space-y-1.5">
        <p className="text-[10px] font-medium text-muted-foreground/60 uppercase tracking-wider">Demo Size</p>
        <div className="flex gap-1.5">
          {presets.map((p) => {
            const Icon = p.icon;
            const isActive = p.id === selectedPreset;
            return (
              <button
                key={p.id}
                onClick={() => setSelectedPreset(p.id)}
                disabled={disabled || previewing}
                className={cn(
                  "flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs font-medium transition-all",
                  isActive
                    ? "border-primary/50 bg-primary/10 text-primary"
                    : "border-border/40 text-muted-foreground hover:border-border/70 hover:text-foreground"
                )}
              >
                <Icon className="h-3 w-3" />
                {p.label}
                <span className={cn("text-[10px] font-normal", isActive ? "text-primary/70" : "text-muted-foreground/40")}>
                  {p.lines.toLocaleString()}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Run button + curated note */}
      <div className="space-y-2">
        <div className="flex items-center gap-3">
          <Button
            onClick={handleRun}
            disabled={disabled || previewing || !selectedDataset}
            className="gap-2 h-9"
          >
            {previewing ? (
              <>
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                Running {dsLabel} Demo...
              </>
            ) : (
              <>
                <Play className="h-3.5 w-3.5" />
                Run {dsLabel} Demo
              </>
            )}
          </Button>

          {previewError && (
            <span className="text-xs text-destructive flex items-center gap-1">
              <AlertCircle className="h-3 w-3" />
              {previewError}
            </span>
          )}
        </div>

        {isCurated && (
          <p className="text-[10px] text-muted-foreground/40 leading-relaxed">
            BGL demos use curated benchmark slices from anomaly-rich regions for a representative demo.
          </p>
        )}
      </div>
    </div>
  );
}

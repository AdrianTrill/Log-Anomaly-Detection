"use client";

import { useState, useEffect } from "react";
import { Loader2, AlertCircle, Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { fetchDatasets, previewDataset } from "@/lib/api";
import type { DatasetInfo, UploadResponse, RunContext } from "@/types/log";

// ── Curated demo presets per dataset ──
// Each preset targets a specific anomaly composition so demos
// are repeatable and meaningful for thesis presentation.

interface PresetConfig {
  id: string;
  label: string;
  description: string;
  lines: number;
  startLine: number;
}

const PRESETS: Record<string, PresetConfig[]> = {
  HDFS_v1: [
    {
      id: "mixed",
      label: "Mixed Sample",
      description: "Balanced normal and anomalous block sessions",
      lines: 1000,
      startLine: 1,
    },
    {
      id: "anomaly_heavy",
      label: "Anomaly-Heavy",
      description: "Dense anomaly region (~27% flagged)",
      lines: 500,
      startLine: 1,
    },
    {
      id: "normal_heavy",
      label: "Normal-Heavy",
      description: "Predominantly normal activity",
      lines: 500,
      startLine: 50001,
    },
  ],
  BGL: [
    {
      id: "mixed",
      label: "Mixed Sample",
      description: "Balanced normal and anomalous windows",
      lines: 1000,
      startLine: 14001,
    },
    {
      id: "anomaly_heavy",
      label: "Anomaly-Heavy",
      description: "Dense anomaly region from later in the log",
      lines: 500,
      startLine: 75051,
    },
    {
      id: "normal_heavy",
      label: "Normal-Heavy",
      description: "Early region with mostly normal entries",
      lines: 500,
      startLine: 1,
    },
  ],
};

const DEFAULT_PRESETS: PresetConfig[] = [
  { id: "mixed", label: "Mixed Sample", description: "Default sample", lines: 1000, startLine: 1 },
];

const DATASET_META: Record<string, { label: string; tag: string; desc: string }> = {
  HDFS_v1: {
    label: "HDFS",
    tag: "Block-session",
    desc: "Hadoop distributed file system logs \u2014 anomaly detection per block session",
  },
  BGL: {
    label: "BGL",
    tag: "Sliding-window",
    desc: "Blue Gene/L supercomputer logs \u2014 anomaly detection per sliding window",
  },
};

interface ModelOption {
  id: string;
  label: string;
}

const DATASET_MODELS: Record<string, ModelOption[]> = {
  HDFS_v1: [
    { id: "transformer_encoder_hdfs", label: "Transformer Encoder" },
    { id: "logbert_hdfs", label: "LogBERT" },
  ],
  BGL: [
    { id: "transformer_encoder_bgl", label: "Transformer Encoder" },
    { id: "logbert_bgl", label: "LogBERT" },
  ],
};

interface DatasetPreviewProps {
  onResult: (data: UploadResponse, context: RunContext) => void;
  disabled: boolean;
}

export function DatasetPreview({ onResult, disabled }: DatasetPreviewProps) {
  const [datasets, setDatasets] = useState<DatasetInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState("");
  const [selectedDataset, setSelectedDataset] = useState("");
  const [selectedPreset, setSelectedPreset] = useState("mixed");
  const [selectedModel, setSelectedModel] = useState("");
  const [previewing, setPreviewing] = useState(false);
  const [previewError, setPreviewError] = useState("");

  useEffect(() => {
    fetchDatasets()
      .then((res) => {
        setDatasets(res.datasets);
        if (res.datasets.length > 0) {
          const first = res.datasets[0].name;
          setSelectedDataset(first);
          setSelectedModel(DATASET_MODELS[first]?.[0]?.id ?? "");
        }
      })
      .catch((err) => {
        setFetchError(err instanceof Error ? err.message : "Failed to load datasets");
      })
      .finally(() => setLoading(false));
  }, []);

  const presets = PRESETS[selectedDataset] ?? DEFAULT_PRESETS;
  const preset = presets.find((p) => p.id === selectedPreset) ?? presets[0];
  const models = DATASET_MODELS[selectedDataset] ?? [];
  const hasModelChoice = models.length > 1;

  const handleRun = async () => {
    if (!selectedDataset) return;
    setPreviewing(true);
    setPreviewError("");
    try {
      const result = await previewDataset({
        dataset_name: selectedDataset,
        max_lines: preset.lines,
        ...(preset.startLine > 1 ? { start_line: preset.startLine } : {}),
        ...(selectedModel ? { model_name: selectedModel } : {}),
      });

      const meta = DATASET_META[selectedDataset];
      const context: RunContext = {
        datasetName: selectedDataset,
        datasetLabel: meta?.label ?? selectedDataset,
        presetLabel: preset.label,
        modelId: selectedModel,
        startLine: preset.startLine,
        lineCount: preset.lines,
      };

      onResult(result, context);
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
                onClick={() => {
                  setSelectedDataset(d.name);
                  setSelectedPreset("mixed");
                  setSelectedModel(DATASET_MODELS[d.name]?.[0]?.id ?? "");
                }}
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

      {/* Model selector */}
      {hasModelChoice && (
        <div className="space-y-1.5">
          <p className="text-[10px] font-medium text-muted-foreground/60 uppercase tracking-wider">Model</p>
          <div className="flex gap-1.5">
            {models.map((m) => {
              const isActive = m.id === selectedModel;
              return (
                <button
                  key={m.id}
                  onClick={() => setSelectedModel(m.id)}
                  disabled={disabled || previewing}
                  className={cn(
                    "rounded-md border px-3 py-1.5 text-xs font-medium transition-all",
                    isActive
                      ? "border-primary/50 bg-primary/10 text-primary"
                      : "border-border/40 text-muted-foreground hover:border-border/70 hover:text-foreground"
                  )}
                >
                  {m.label}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Curated sample preset selector */}
      <div className="space-y-1.5">
        <p className="text-[10px] font-medium text-muted-foreground/60 uppercase tracking-wider">Sample</p>
        <div className="flex gap-1.5">
          {presets.map((p) => {
            const isActive = p.id === selectedPreset;
            return (
              <button
                key={p.id}
                onClick={() => setSelectedPreset(p.id)}
                disabled={disabled || previewing}
                className={cn(
                  "flex flex-col items-start rounded-md border px-3 py-1.5 text-left transition-all",
                  isActive
                    ? "border-primary/50 bg-primary/10 text-primary"
                    : "border-border/40 text-muted-foreground hover:border-border/70 hover:text-foreground"
                )}
              >
                <span className="text-xs font-medium">{p.label}</span>
                <span className={cn(
                  "text-[10px] font-normal",
                  isActive ? "text-primary/70" : "text-muted-foreground/40"
                )}>
                  {p.lines.toLocaleString()} lines
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Run button */}
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
      </div>
    </div>
  );
}

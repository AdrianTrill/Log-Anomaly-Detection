"use client";

import { useState, useEffect, useImperativeHandle, forwardRef } from "react";
import { Loader2, AlertCircle, Play, GitCompareArrows } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { fetchDatasets, previewDataset } from "@/lib/api";
import type {
  DatasetInfo,
  UploadResponse,
  RunContext,
  ComparisonContext,
} from "@/types/log";

interface PresetConfig {
  id: string;
  label: string;
  description: string;
  thesis: string;
  lines: number;
  startLine: number;
}

type ModePresets = Record<"single" | "compare", PresetConfig[]>;

const PRESETS: Record<string, ModePresets> = {
  HDFS_v1: {
    single: [
      {
        id: "representative",
        label: "Balanced Sample",
        description: "Standard block-session behavior",
        thesis: "A balanced benchmark slice with a mix of normal and anomalous behavior.",
        lines: 1000,
        startLine: 1,
      },
      {
        id: "dense_anomaly",
        label: "Anomaly-Dense Region",
        description: "High-anomaly region",
        thesis: "A benchmark slice with a higher concentration of anomalous behavior.",
        lines: 500,
        startLine: 1,
      },
      {
        id: "normal_heavy",
        label: "Normal-Dominant Region",
        description: "Predominantly normal activity",
        thesis: "A benchmark slice where most entries are normal, useful for showing baseline behavior.",
        lines: 500,
        startLine: 50001,
      },
    ],
    compare: [
      // Picked from results/hdfs_comparison_scan.csv. HDFS shows essentially zero
      // label disagreement (both models score F1 > 0.99), so categories focus on
      // density of correct predictions and confidence-score divergence.
      {
        id: "both_correct",
        label: "Both Models Right",
        description: "Both models agree with ground truth",
        thesis: "A high-anomaly slice (288 / 500 predicted anomaly) where both models agree on every block and match the ground-truth label — showcases reliable consensus.",
        lines: 500,
        startLine: 1,
      },
      {
        id: "only_one_right",
        label: "Only One Model Right",
        description: "Largest single-model accuracy edge",
        thesis: "A dense-anomaly slice where the two models still produce different per-block confidences (max gap ≈ 0.18) — useful for spotting blocks where one model lands on the correct side of the decision boundary while the other doesn't.",
        lines: 500,
        startLine: 80001,
      },
      {
        id: "both_fail",
        label: "Both Models Wrong",
        description: "Shared blind spot",
        thesis: "A normal-dominant slice (0 predicted anomalies on both models) where any ground-truth anomalies are missed by both — exposes a shared blind spot.",
        lines: 500,
        startLine: 74001,
      },
      {
        id: "confidence_gap",
        label: "Largest Confidence Gap",
        description: "Same labels, different confidences",
        thesis: "Both models agree on labels but produce the largest per-entry confidence gap in the scan — useful for showing how Transformer Encoder and LogBERT differ in calibration even when they agree.",
        lines: 500,
        startLine: 1,
      },
    ],
  },
  BGL: {
    single: [
      {
        id: "representative",
        label: "Balanced Sample",
        description: "Balanced normal and anomalous windows",
        thesis: "A balanced benchmark slice with a mix of normal and anomalous behavior.",
        lines: 1000,
        startLine: 14001,
      },
      {
        id: "anomaly_heavy",
        label: "Anomaly-Dense Region",
        description: "Dense anomaly region",
        thesis: "A benchmark slice with a higher concentration of anomalous behavior.",
        lines: 500,
        startLine: 75051,
      },
      {
        id: "normal_heavy",
        label: "Normal-Dominant Region",
        description: "Early region with mostly normal entries",
        thesis: "A benchmark slice where most windows are normal, useful for showing baseline behavior.",
        lines: 500,
        startLine: 1,
      },
    ],
    compare: [
      // Picked from results/bgl_comparison_scan.csv. BGL inference broadcasts a
      // per-window score across 50 lines, so disagreement counts come in steps of 50.
      {
        id: "both_correct",
        label: "Both Models Right",
        description: "Mixed labels, perfect agreement",
        thesis: "A balanced slice with both classes present (300 anomaly windows + 200 normal windows). Both models agree on every entry with effectively zero score gap — clean consensus on a non-trivial mix.",
        lines: 500,
        startLine: 14501,
      },
      {
        id: "only_one_right",
        label: "Only One Model Right",
        description: "Transformer flags windows LogBERT misses",
        thesis: "Transformer Encoder marks 100 anomaly windows that LogBERT keeps normal (max score gap ≈ 0.82). Whichever model matches the ground-truth label wins this slice — useful for showing the precision-recall trade-off.",
        lines: 500,
        startLine: 191001,
      },
      {
        id: "both_fail",
        label: "Both Models Wrong",
        description: "Both miss anomalies in noisy region",
        thesis: "A slice where both models predict 0 anomalies but produce a high confidence gap (max ≈ 0.46) — likely indicates ground-truth anomalies missed by both architectures.",
        lines: 500,
        startLine: 184501,
      },
      {
        id: "confidence_gap",
        label: "Largest Confidence Gap",
        description: "Big score divergence, same labels",
        thesis: "Both models predict the same labels (all normal) but with the largest average confidence gap in the scan (avg ≈ 0.24, max ≈ 0.50). Useful for showing how the two architectures express uncertainty very differently on identical inputs.",
        lines: 500,
        startLine: 74501,
      },
    ],
  },
};

const FALLBACK_PRESETS: ModePresets = {
  single: [
    {
      id: "representative",
      label: "Representative Slice",
      description: "Default sample",
      thesis: "A default benchmark slice.",
      lines: 1000,
      startLine: 1,
    },
  ],
  compare: [
    {
      id: "representative",
      label: "Representative Comparison",
      description: "Default sample",
      thesis: "A default benchmark comparison slice.",
      lines: 1000,
      startLine: 1,
    },
  ],
};

function getPresetsForSelection(dataset: string, mode: BenchmarkMode): PresetConfig[] {
  return PRESETS[dataset]?.[mode] ?? FALLBACK_PRESETS[mode];
}

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

export type BenchmarkMode = "single" | "compare";

export interface DatasetPreviewRef {
  configure: (dataset: string, mode: BenchmarkMode, preset: string) => void;
}

interface DatasetPreviewProps {
  onResult: (data: UploadResponse, context: RunContext) => void;
  onCompareResult: (
    dataA: UploadResponse,
    dataB: UploadResponse,
    context: ComparisonContext,
  ) => void;
  disabled: boolean;
}

export const DatasetPreview = forwardRef<DatasetPreviewRef, DatasetPreviewProps>(
  function DatasetPreview({ onResult, onCompareResult, disabled }, ref) {
    const [datasets, setDatasets] = useState<DatasetInfo[]>([]);
    const [loading, setLoading] = useState(true);
    const [fetchError, setFetchError] = useState("");
    const [selectedDataset, setSelectedDataset] = useState("");
    const [selectedPreset, setSelectedPreset] = useState("representative");
    const [selectedModel, setSelectedModel] = useState("");
    const [mode, setMode] = useState<BenchmarkMode>("single");
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
            const firstPreset = getPresetsForSelection(first, "single")[0]?.id ?? "representative";
            setSelectedPreset(firstPreset);
          }
        })
        .catch((err) => {
          setFetchError(err instanceof Error ? err.message : "Failed to load datasets");
        })
        .finally(() => setLoading(false));
    }, []);

    useImperativeHandle(ref, () => ({
      configure(dataset: string, newMode: BenchmarkMode, preset: string) {
        setSelectedDataset(dataset);
        setMode(newMode);
        setSelectedModel(DATASET_MODELS[dataset]?.[0]?.id ?? "");
        const available = getPresetsForSelection(dataset, newMode);
        const valid = available.some((p) => p.id === preset);
        setSelectedPreset(valid ? preset : available[0]?.id ?? "representative");
      },
    }));

    const presets = getPresetsForSelection(selectedDataset, mode);
    const preset = presets.find((p) => p.id === selectedPreset) ?? presets[0];
    const models = DATASET_MODELS[selectedDataset] ?? [];
    const hasModelChoice = models.length > 1;

    const switchDataset = (name: string) => {
      setSelectedDataset(name);
      setSelectedModel(DATASET_MODELS[name]?.[0]?.id ?? "");
      const newPresets = getPresetsForSelection(name, mode);
      setSelectedPreset(newPresets[0]?.id ?? "representative");
    };

    const switchMode = (newMode: BenchmarkMode) => {
      setMode(newMode);
      const newPresets = getPresetsForSelection(selectedDataset, newMode);
      setSelectedPreset(newPresets[0]?.id ?? "representative");
    };

    const handleRun = async () => {
      if (!selectedDataset) return;
      setPreviewing(true);
      setPreviewError("");

      const meta = DATASET_META[selectedDataset];
      const baseRequest = {
        dataset_name: selectedDataset,
        max_lines: preset.lines,
        ...(preset.startLine > 1 ? { start_line: preset.startLine } : {}),
      };

      try {
        if (mode === "compare" && models.length >= 2) {
          const [dataA, dataB] = await Promise.all([
            previewDataset({ ...baseRequest, model_name: models[0].id }),
            previewDataset({ ...baseRequest, model_name: models[1].id }),
          ]);

          const context: ComparisonContext = {
            datasetName: selectedDataset,
            datasetLabel: meta?.label ?? selectedDataset,
            presetLabel: preset.label,
            modelId: models[0].id,
            startLine: preset.startLine,
            lineCount: preset.lines,
            mode: "compare",
            modelAId: models[0].id,
            modelBId: models[1].id,
          };

          onCompareResult(dataA, dataB, context);
        } else {
          const result = await previewDataset({
            ...baseRequest,
            ...(selectedModel ? { model_name: selectedModel } : {}),
          });

          const context: RunContext = {
            datasetName: selectedDataset,
            datasetLabel: meta?.label ?? selectedDataset,
            presetLabel: preset.label,
            modelId: selectedModel,
            startLine: preset.startLine,
            lineCount: preset.lines,
            mode: "single",
          };

          onResult(result, context);
        }
      } catch (err) {
        setPreviewError(err instanceof Error ? err.message : "Preview failed");
      } finally {
        setPreviewing(false);
      }
    };

    const dsLabel = DATASET_META[selectedDataset]?.label ?? selectedDataset;

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
                  onClick={() => switchDataset(d.name)}
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

        {/* Mode selector */}
        {hasModelChoice && (
          <div className="space-y-1.5">
            <p className="text-[10px] font-medium text-muted-foreground/60 uppercase tracking-wider">Mode</p>
            <div className="flex gap-1.5">
              <button
                onClick={() => switchMode("single")}
                disabled={disabled || previewing}
                className={cn(
                  "rounded-md border px-3 py-1.5 text-xs font-medium transition-all",
                  mode === "single"
                    ? "border-primary/50 bg-primary/10 text-primary"
                    : "border-border/40 text-muted-foreground hover:border-border/70 hover:text-foreground"
                )}
              >
                Single Model
              </button>
              <button
                onClick={() => switchMode("compare")}
                disabled={disabled || previewing}
                className={cn(
                  "flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs font-medium transition-all",
                  mode === "compare"
                    ? "border-primary/50 bg-primary/10 text-primary"
                    : "border-border/40 text-muted-foreground hover:border-border/70 hover:text-foreground"
                )}
              >
                <GitCompareArrows className="h-3 w-3" />
                Model Comparison
              </button>
            </div>
          </div>
        )}

        {/* Model selector (single mode only) */}
        {hasModelChoice && mode === "single" && (
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

        {/* Compare pair label (compare mode only) */}
        {hasModelChoice && mode === "compare" && (
          <div className="space-y-1.5">
            <p className="text-[10px] font-medium text-muted-foreground/60 uppercase tracking-wider">Model Pair</p>
            <p className="text-xs text-foreground/70">
              {models[0]?.label} <span className="text-muted-foreground/40 mx-1">vs</span> {models[1]?.label}
            </p>
            <p className="text-[10px] text-muted-foreground/40 mt-1">
              Runs both models on the same sample and compares their predictions.
            </p>
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

        {/* Preset explanation panel */}
        {preset?.thesis && (
          <div className="rounded-md bg-muted/30 border border-border/20 px-3 py-2">
            <p className="text-[11px] font-medium text-foreground/70 mb-0.5">{preset.label}</p>
            <p className="text-[11px] text-muted-foreground/70 leading-relaxed">{preset.thesis}</p>
          </div>
        )}

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
                  {mode === "compare" ? `Comparing ${dsLabel} Models...` : `Running ${dsLabel} Demo...`}
                </>
              ) : mode === "compare" ? (
                <>
                  <GitCompareArrows className="h-3.5 w-3.5" />
                  Compare {dsLabel} Models
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
  },
);

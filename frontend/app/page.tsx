"use client";

import { useState, useCallback } from "react";
import {
  Loader2,
  AlertCircle,
  RotateCcw,
  Upload,
  FlaskConical,
  Brain,
  FileText,
  ChevronDown,
  GitCompareArrows,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { FileDropzone } from "@/components/upload/FileDropzone";
import { SampleDataButton } from "@/components/upload/SampleDataButton";
import { DatasetPreview } from "@/components/upload/DatasetPreview";
import { DashboardView } from "@/components/dashboard/DashboardView";
import { ComparisonView } from "@/components/dashboard/ComparisonView";
import { RunMetaStrip } from "@/components/dashboard/RunMetaStrip";
import { uploadLogFile } from "@/lib/api";
import { formatModelName, shortModelLabel } from "@/lib/inference";
import type { UploadResponse, RunContext, ComparisonContext } from "@/types/log";

type DataSource = "upload" | "sample" | "dataset";

interface ResultMeta {
  source: DataSource;
  data: UploadResponse;
  context?: RunContext;
}

interface ComparisonResultMeta {
  source: "dataset";
  dataA: UploadResponse;
  dataB: UploadResponse;
  context: ComparisonContext;
}

export default function HomePage() {
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [result, setResult] = useState<ResultMeta | null>(null);
  const [comparisonResult, setComparisonResult] = useState<ComparisonResultMeta | null>(null);
  const [error, setError] = useState("");
  const [customOpen, setCustomOpen] = useState(false);

  const isLoading = uploading;

  const handleFileSelect = useCallback((file: File) => {
    setSelectedFile(file);
    setError("");
  }, []);

  const handleClear = useCallback(() => {
    setSelectedFile(null);
    setError("");
  }, []);

  const handleUpload = useCallback(async () => {
    if (!selectedFile) return;
    setUploading(true);
    setError("");
    try {
      const data = await uploadLogFile(selectedFile);
      setResult({ source: "upload", data });
      setComparisonResult(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An unexpected error occurred");
    } finally {
      setUploading(false);
    }
  }, [selectedFile]);

  const handleSampleSelect = useCallback((file: File) => {
    setSelectedFile(file);
    setError("");
    setUploading(true);
    uploadLogFile(file)
      .then((data) => {
        setResult({ source: "sample", data });
        setComparisonResult(null);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "An unexpected error occurred"))
      .finally(() => setUploading(false));
  }, []);

  const handleDatasetResult = useCallback((data: UploadResponse, context: RunContext) => {
    setResult({ source: "dataset", data, context });
    setComparisonResult(null);
    setError("");
  }, []);

  const handleCompareResult = useCallback(
    (dataA: UploadResponse, dataB: UploadResponse, context: ComparisonContext) => {
      setComparisonResult({ source: "dataset", dataA, dataB, context });
      setResult(null);
      setError("");
    },
    [],
  );

  const handleReset = useCallback(() => {
    setResult(null);
    setComparisonResult(null);
    setSelectedFile(null);
    setError("");
    setUploading(false);
  }, []);

  /* ─── Comparison results view ─── */
  if (comparisonResult) {
    const { dataA, dataB, context } = comparisonResult;
    const modelAShort = shortModelLabel(context.modelAId);
    const modelBShort = shortModelLabel(context.modelBId);

    return (
      <div className="container px-6 mx-auto py-8">
        <div className="flex items-center justify-between gap-4 mb-2">
          <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1.5 min-w-0">
            <Badge variant="default" className="text-[10px] gap-1 py-0.5 shrink-0">
              <GitCompareArrows className="h-3 w-3" />
              Comparison
            </Badge>
            <span className="text-sm font-medium truncate">
              {context.datasetLabel} &mdash; {modelAShort} vs {modelBShort}
            </span>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleReset}
            className="gap-1.5 text-xs text-muted-foreground hover:text-foreground shrink-0 h-8"
          >
            <RotateCcw className="h-3 w-3" />
            Reset
          </Button>
        </div>

        <div className="mb-3">
          <RunMetaStrip
            context={context}
            inferenceSummary={dataA.inference_summary ?? null}
            comparisonContext={context}
            inferenceSummaryB={dataB.inference_summary ?? null}
          />
        </div>

        <ComparisonView dataA={dataA} dataB={dataB} context={context} />
      </div>
    );
  }

  /* ─── Single-model results view ─── */
  if (result) {
    const { source, data, context } = result;
    const isBenchmark = source === "dataset" && !!context;

    const headerLabel = isBenchmark
      ? `${context.datasetLabel} \u2014 ${formatModelName(data.inference_summary?.model_name ?? context.modelId)}`
      : source === "sample"
        ? "Sample Log"
        : data.file_name;

    return (
      <div className="container px-6 mx-auto py-8">
        <div className="flex items-center justify-between gap-4 mb-4">
          <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1.5 min-w-0">
            <Badge
              variant={isBenchmark ? "default" : "secondary"}
              className="text-[10px] gap-1 py-0.5 shrink-0"
            >
              {isBenchmark ? (
                <FlaskConical className="h-3 w-3" />
              ) : (
                <Upload className="h-3 w-3" />
              )}
              {isBenchmark ? "Benchmark" : source === "sample" ? "Sample" : "Upload"}
            </Badge>
            <span className="text-sm font-medium truncate">{headerLabel}</span>
            {!isBenchmark && (
              <span className="text-xs text-muted-foreground tabular-nums">
                {data.total_lines.toLocaleString()} lines
              </span>
            )}
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleReset}
            className="gap-1.5 text-xs text-muted-foreground hover:text-foreground shrink-0 h-8"
          >
            <RotateCcw className="h-3 w-3" />
            Reset
          </Button>
        </div>

        {isBenchmark && (
          <div className="mb-6">
            <RunMetaStrip
              context={context}
              inferenceSummary={data.inference_summary ?? null}
            />
          </div>
        )}

        <DashboardView data={data} isBenchmark={isBenchmark} />
      </div>
    );
  }

  /* ─── Entry page ─── */
  return (
    <div className="container px-6 mx-auto py-10 sm:py-14">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">
            Log Anomaly Detection
          </h1>
          <p className="mt-2 text-sm text-muted-foreground max-w-lg mx-auto leading-relaxed">
            Transformer-based anomaly detection on benchmark log datasets.
          </p>
        </div>

        <div className="space-y-4">
          {/* ── Primary: Benchmark Evaluation ── */}
          <Card className="border-border/60 shadow-sm">
            <CardHeader className="pb-2 pt-4 px-5">
              <CardTitle className="flex items-center gap-2 text-sm font-semibold">
                <div className="flex h-6 w-6 items-center justify-center rounded-md bg-primary/10">
                  <Brain className="h-3 w-3 text-primary" />
                </div>
                Benchmark Evaluation
              </CardTitle>
              <p className="text-[11px] text-muted-foreground/70 mt-1">
                Run trained anomaly detection models on benchmark log datasets (HDFS, BGL).
              </p>
            </CardHeader>
            <CardContent className="px-5 pb-5">
              <DatasetPreview
                onResult={handleDatasetResult}
                onCompareResult={handleCompareResult}
                disabled={isLoading}
              />
            </CardContent>
          </Card>

          {/* ── Secondary: Custom Upload (collapsible) ── */}
          <Card className="border-border/30 border-dashed">
            <button
              onClick={() => setCustomOpen(!customOpen)}
              className="w-full flex items-center justify-between px-5 py-4 text-left"
            >
              <div className="flex items-center gap-2">
                <div className="flex h-6 w-6 items-center justify-center rounded-md bg-muted">
                  <FileText className="h-3 w-3 text-muted-foreground" />
                </div>
                <div>
                  <span className="text-sm font-semibold text-muted-foreground">Custom Log Inspection</span>
                  <p className="text-[10px] text-muted-foreground/40 mt-0.5">
                    Upload any log file for parsing and inspection &mdash; no trained model inference
                  </p>
                </div>
              </div>
              <ChevronDown className={`h-4 w-4 text-muted-foreground/40 transition-transform ${customOpen ? "rotate-180" : ""}`} />
            </button>

            {customOpen && (
              <CardContent className="px-5 pb-5 pt-0 space-y-3">
                <FileDropzone
                  onFileSelect={handleFileSelect}
                  selectedFile={selectedFile}
                  onClear={handleClear}
                  isUploading={uploading}
                />

                <div className="flex items-center gap-3">
                  <SampleDataButton
                    onFileSelect={handleSampleSelect}
                    disabled={isLoading}
                  />
                  <div className="ml-auto">
                    <Button
                      onClick={handleUpload}
                      disabled={!selectedFile || isLoading}
                      variant="secondary"
                      className="gap-2"
                    >
                      {uploading ? (
                        <>
                          <Loader2 className="h-4 w-4 animate-spin" />
                          Parsing...
                        </>
                      ) : (
                        "Upload & Parse"
                      )}
                    </Button>
                  </div>
                </div>

                <p className="text-[10px] text-muted-foreground/40 leading-relaxed">
                  Custom uploads are parsed and inspected only. Trained anomaly detection models are not applied to arbitrary uploads &mdash; use the benchmark evaluation above for model inference.
                </p>
              </CardContent>
            )}
          </Card>
        </div>

        {error && (
          <div className="mt-4 rounded-lg border border-destructive/50 bg-destructive/10 p-3.5 flex items-start gap-3">
            <AlertCircle className="h-4 w-4 text-destructive shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-xs text-destructive">Operation failed</p>
              <p className="text-xs text-muted-foreground mt-0.5">{error}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

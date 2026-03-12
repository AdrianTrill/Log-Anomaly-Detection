"use client";

import { useState, useCallback } from "react";
import {
  Loader2,
  AlertCircle,
  RotateCcw,
  Clock,
  CheckCircle2,
  Upload,
  FlaskConical,
  ChevronRight,
  ArrowRight,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { FileDropzone } from "@/components/upload/FileDropzone";
import { SampleDataButton } from "@/components/upload/SampleDataButton";
import { DatasetPreview } from "@/components/upload/DatasetPreview";
import { DashboardView } from "@/components/dashboard/DashboardView";
import { uploadLogFile } from "@/lib/api";
import type { UploadResponse } from "@/types/log";

type DataSource = "upload" | "sample" | "dataset";

interface ResultMeta {
  source: DataSource;
  data: UploadResponse;
}

const PIPELINE_STEPS = ["Upload", "Parse", "Inspect", "Detect"] as const;

export default function HomePage() {
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [result, setResult] = useState<ResultMeta | null>(null);
  const [error, setError] = useState("");
  const [datasetOpen, setDatasetOpen] = useState(false);

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
      .then((data) => setResult({ source: "sample", data }))
      .catch((err) => setError(err instanceof Error ? err.message : "An unexpected error occurred"))
      .finally(() => setUploading(false));
  }, []);

  const handleDatasetResult = useCallback((data: UploadResponse) => {
    setResult({ source: "dataset", data });
    setError("");
  }, []);

  const handleReset = useCallback(() => {
    setResult(null);
    setSelectedFile(null);
    setError("");
    setUploading(false);
  }, []);

  if (result) {
    const { source, data } = result;
    const parseRate = data.total_lines > 0
      ? Math.round((data.parsed_lines / data.total_lines) * 100)
      : 0;

    const sourceLabel = source === "dataset"
      ? "Benchmark"
      : source === "sample"
        ? "Sample"
        : "Upload";

    return (
      <div className="container px-6 mx-auto py-8">
        <div className="flex items-center justify-between gap-4 mb-8">
          <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1.5 min-w-0">
            <Badge
              variant={source === "dataset" ? "default" : "secondary"}
              className="text-[10px] gap-1 py-0.5 shrink-0"
            >
              {source === "dataset" ? (
                <FlaskConical className="h-3 w-3" />
              ) : (
                <Upload className="h-3 w-3" />
              )}
              {sourceLabel}
            </Badge>
            <span className="text-sm font-medium truncate">{data.file_name}</span>
            <span className="text-xs text-muted-foreground tabular-nums">
              {data.total_lines.toLocaleString()} lines
            </span>
            <Badge variant="secondary" className="text-[10px] gap-1 py-0.5 shrink-0">
              <CheckCircle2 className="h-3 w-3 text-emerald-500" />
              {parseRate}%
            </Badge>
            {data.time_range?.earliest && (
              <span className="text-[11px] text-muted-foreground/70 font-mono tabular-nums hidden sm:inline">
                {data.time_range.earliest} &ndash; {data.time_range.latest}
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
        <DashboardView data={data} />
      </div>
    );
  }

  return (
    <div className="container px-6 mx-auto py-10 sm:py-14">
      <div className="max-w-xl mx-auto">
        {/* Title area */}
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">
            Log Anomaly Detection
          </h1>
          <p className="mt-2 text-sm text-muted-foreground max-w-md mx-auto leading-relaxed">
            Parse and normalize log files, inspect structured results, and
            prepare entries for transformer-based anomaly detection.
          </p>

          {/* Pipeline steps */}
          <div className="flex items-center justify-center gap-1 mt-4">
            {PIPELINE_STEPS.map((step, i) => (
              <div key={step} className="flex items-center gap-1">
                <span className={`text-[10px] tracking-wide font-medium ${
                  i === 0 ? "text-foreground/80" : "text-muted-foreground/50"
                }`}>
                  {step}
                </span>
                {i < PIPELINE_STEPS.length - 1 && (
                  <ArrowRight className="h-2.5 w-2.5 text-muted-foreground/30" />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Primary upload card */}
        <Card className="border-border/60 shadow-sm">
          <CardHeader className="pb-2 pt-5 px-5">
            <CardTitle className="flex items-center gap-2 text-sm font-semibold">
              <div className="flex h-6 w-6 items-center justify-center rounded-md bg-primary/10">
                <Upload className="h-3 w-3 text-primary" />
              </div>
              Upload Log File
            </CardTitle>
          </CardHeader>
          <CardContent className="px-5 pb-5 space-y-3">
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

            <p className="text-[10px] text-muted-foreground/50 leading-relaxed text-center pt-1">
              Supports structured, bracketed, syslog, and ISO 8601 log formats.
              Use <span className="font-medium text-muted-foreground/70">Load Sample Data</span> for a quick demo.
            </p>
          </CardContent>
        </Card>

        {/* Secondary benchmark section */}
        <Collapsible open={datasetOpen} onOpenChange={setDatasetOpen} className="mt-3">
          <CollapsibleTrigger className="flex items-center gap-2 w-full rounded-lg border border-border/30 bg-card/30 px-4 py-2 text-muted-foreground/70 hover:text-muted-foreground hover:bg-card/60 transition-colors cursor-pointer">
            <ChevronRight className={`h-3 w-3 transition-transform ${datasetOpen ? "rotate-90" : ""}`} />
            <FlaskConical className="h-3 w-3" />
            <span className="text-[11px] font-medium">Benchmark Datasets</span>
            <span className="text-[10px] text-muted-foreground/40 ml-0.5">HDFS, BGL</span>
            <span className="text-[10px] text-muted-foreground/30 ml-auto">research preview</span>
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-2">
            <DatasetPreview
              onResult={handleDatasetResult}
              disabled={isLoading}
            />
          </CollapsibleContent>
        </Collapsible>

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

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
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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

export default function HomePage() {
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [result, setResult] = useState<ResultMeta | null>(null);
  const [error, setError] = useState("");

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
      <div className="max-w-2xl mx-auto">
        {/* Title */}
        <div className="text-center mb-10">
          <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">
            Log Anomaly Detection
          </h1>
          <p className="mt-2 text-sm text-muted-foreground max-w-lg mx-auto leading-relaxed">
            Research workbench for transformer-based anomaly detection on benchmark log datasets.
          </p>
        </div>

        <div className="space-y-4">
          {/* Primary: Benchmark Inference */}
          <Card className="border-border/60 shadow-sm">
            <CardHeader className="pb-2 pt-5 px-5">
              <CardTitle className="flex items-center gap-2 text-sm font-semibold">
                <div className="flex h-6 w-6 items-center justify-center rounded-md bg-primary/10">
                  <Brain className="h-3 w-3 text-primary" />
                </div>
                Benchmark Inference
              </CardTitle>
              <p className="text-[11px] text-muted-foreground/70 mt-1">
                Run trained models on supported benchmark datasets and inspect anomaly predictions.
              </p>
            </CardHeader>
            <CardContent className="px-5 pb-5 space-y-3">
              <div className="flex items-center gap-2 mb-1">
                <Badge variant="secondary" className="text-[10px] py-0 gap-1">
                  <FlaskConical className="h-2.5 w-2.5" />
                  HDFS
                </Badge>
                <Badge variant="outline" className="text-[10px] py-0 text-muted-foreground/50 border-dashed">
                  BGL — next
                </Badge>
              </div>
              <DatasetPreview
                onResult={handleDatasetResult}
                disabled={isLoading}
              />
            </CardContent>
          </Card>

          {/* Secondary: Custom Log Parsing */}
          <Card className="border-border/30 border-dashed">
            <CardHeader className="pb-2 pt-5 px-5">
              <CardTitle className="flex items-center gap-2 text-sm font-semibold text-muted-foreground">
                <div className="flex h-6 w-6 items-center justify-center rounded-md bg-muted">
                  <FileText className="h-3 w-3 text-muted-foreground" />
                </div>
                Custom Log Parsing
              </CardTitle>
              <p className="text-[11px] text-muted-foreground/50 mt-1">
                Upload any log file for parsing, normalization, and structured inspection.
                Anomaly inference is not yet available for arbitrary uploads.
              </p>
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
            </CardContent>
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

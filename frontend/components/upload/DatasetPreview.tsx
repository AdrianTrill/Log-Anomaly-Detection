"use client";

import { useState, useEffect } from "react";
import { Loader2, Database, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { fetchDatasets, previewDataset } from "@/lib/api";
import type { DatasetInfo, UploadResponse } from "@/types/log";

const LINE_OPTIONS = [100, 200, 500, 1000];

interface DatasetPreviewProps {
  onResult: (data: UploadResponse) => void;
  disabled: boolean;
}

export function DatasetPreview({ onResult, disabled }: DatasetPreviewProps) {
  const [datasets, setDatasets] = useState<DatasetInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState("");
  const [selectedDataset, setSelectedDataset] = useState("");
  const [maxLines, setMaxLines] = useState(200);
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

  const handlePreview = async () => {
    if (!selectedDataset) return;
    setPreviewing(true);
    setPreviewError("");
    try {
      const result = await previewDataset({
        dataset_name: selectedDataset,
        max_lines: maxLines,
      });
      onResult(result);
    } catch (err) {
      setPreviewError(err instanceof Error ? err.message : "Preview failed");
    } finally {
      setPreviewing(false);
    }
  };

  const selected = datasets.find((d) => d.name === selectedDataset);

  return (
    <div className="rounded-lg border border-border/40 bg-card/50 p-4 space-y-3">
      {loading ? (
        <div className="flex items-center gap-2 text-xs text-muted-foreground py-2 justify-center">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          Loading datasets...
        </div>
      ) : fetchError ? (
        <div className="flex items-start gap-2 text-xs py-1">
          <AlertCircle className="h-3.5 w-3.5 text-destructive shrink-0 mt-0.5" />
          <span className="text-muted-foreground">{fetchError}</span>
        </div>
      ) : datasets.length === 0 ? (
        <div className="flex items-start gap-2 text-xs py-1">
          <Database className="h-3.5 w-3.5 text-muted-foreground shrink-0 mt-0.5" />
          <span className="text-muted-foreground">
            No datasets found. Place log files in <code className="text-[10px] bg-muted px-1 py-0.5 rounded">datasets/raw/</code>.
          </span>
        </div>
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-[1fr_120px]">
            <div className="space-y-1">
              <label className="text-[10px] font-medium text-muted-foreground/60 uppercase tracking-wider">Dataset</label>
              <Select value={selectedDataset} onValueChange={(v) => v && setSelectedDataset(v)}>
                <SelectTrigger className="w-full h-8 text-xs">
                  <SelectValue placeholder="Select dataset" />
                </SelectTrigger>
                <SelectContent>
                  {datasets.map((d) => (
                    <SelectItem key={d.name} value={d.name}>
                      <span className="flex items-center gap-2">
                        {d.name}
                        <Badge variant="outline" className="text-[9px] py-0 px-1.5 font-normal">
                          {d.format.toUpperCase()}
                        </Badge>
                      </span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1">
              <label className="text-[10px] font-medium text-muted-foreground/60 uppercase tracking-wider">Lines</label>
              <Select
                value={String(maxLines)}
                onValueChange={(v) => v && setMaxLines(Number(v))}
              >
                <SelectTrigger className="w-full h-8 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {LINE_OPTIONS.map((n) => (
                    <SelectItem key={n} value={String(n)}>
                      {n.toLocaleString()}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {selected && (
            <p className="text-[10px] text-muted-foreground/60 leading-relaxed">
              {selected.description}
              {" "}Preview loads a subset of lines for dashboard responsiveness.
            </p>
          )}

          <div className="flex items-center gap-3">
            <Button
              size="sm"
              variant="secondary"
              onClick={handlePreview}
              disabled={disabled || previewing || !selectedDataset}
              className="gap-1.5 text-xs h-8"
            >
              {previewing ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  Loading...
                </>
              ) : (
                <>
                  <Database className="h-3.5 w-3.5" />
                  Load Preview
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
        </>
      )}
    </div>
  );
}

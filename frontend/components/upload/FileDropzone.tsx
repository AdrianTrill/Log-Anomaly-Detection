"use client";

import { useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, FileText, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface FileDropzoneProps {
  onFileSelect: (file: File) => void;
  selectedFile: File | null;
  onClear: () => void;
  isUploading: boolean;
}

export function FileDropzone({ onFileSelect, selectedFile, onClear, isUploading }: FileDropzoneProps) {
  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      if (acceptedFiles.length > 0) {
        onFileSelect(acceptedFiles[0]);
      }
    },
    [onFileSelect]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "text/plain": [".log", ".txt"] },
    maxFiles: 1,
    disabled: isUploading,
  });

  if (selectedFile) {
    return (
      <div className="rounded-lg border border-primary/30 bg-primary/5 p-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
              <FileText className="h-4 w-4 text-primary" />
            </div>
            <div>
              <p className="font-medium text-sm">{selectedFile.name}</p>
              <p className="text-[11px] text-muted-foreground">
                {(selectedFile.size / 1024).toFixed(1)} KB &middot; Ready to parse
              </p>
            </div>
          </div>
          {!isUploading && (
            <Button variant="ghost" size="icon" onClick={onClear} className="h-8 w-8 text-muted-foreground hover:text-foreground">
              <X className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div
      {...getRootProps()}
      className={cn(
        "cursor-pointer rounded-lg border-2 border-dashed p-6 text-center transition-all",
        isDragActive
          ? "border-primary bg-primary/5 scale-[1.01]"
          : "border-muted-foreground/20 hover:border-primary/40 hover:bg-muted/30"
      )}
    >
      <input {...getInputProps()} />
      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted mx-auto mb-3">
        <Upload className="h-5 w-5 text-muted-foreground" />
      </div>
      <p className="font-medium text-sm">
        {isDragActive ? "Drop your log file here" : "Drag & drop a log file"}
      </p>
      <p className="mt-1 text-[11px] text-muted-foreground">
        or click to browse
      </p>
      <div className="flex justify-center gap-1.5 mt-3">
        <Badge variant="secondary" className="text-[10px] font-normal px-2 py-0">.log</Badge>
        <Badge variant="secondary" className="text-[10px] font-normal px-2 py-0">.txt</Badge>
      </div>
    </div>
  );
}

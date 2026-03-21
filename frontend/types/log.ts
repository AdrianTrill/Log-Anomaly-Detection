export interface LogEntry {
  id: string;
  line_number: number;
  raw_line: string;
  timestamp: string | null;
  level: string | null;
  source: string | null;
  message: string | null;
  normalized_message: string | null;
  parse_status: "parsed" | "fallback";
  anomaly_score: number | null;
  prediction: string | null;
  explanation: string | null;
  model_name: string | null;
  inference_status: "not_run" | "not_available" | "completed" | "error";
}

export interface NormalizationInfo {
  ip_masked: number;
  num_masked: number;
  uuid_masked: number;
  levels_standardized: number;
}

export interface TimeRange {
  earliest: string | null;
  latest: string | null;
}

export interface InferenceSummary {
  model_name: string;
  entries_analyzed: number;
  anomalies_detected: number;
  status: string;
  scope: string;
}

export interface UploadResponse {
  file_name: string;
  total_lines: number;
  parsed_lines: number;
  failed_lines: number;
  level_distribution: Record<string, number>;
  source_distribution: Record<string, number>;
  time_range: TimeRange | null;
  entries: LogEntry[];
  normalization_info: NormalizationInfo;
  ai_ready: boolean;
  inference_summary: InferenceSummary | null;
}

export interface ModelInfo {
  model_name: string;
  status: string;
  description: string;
}

export interface HealthResponse {
  status: string;
  version: string;
  models: ModelInfo[];
}

export interface AnalysisResponse {
  model_name: string;
  status: string;
  entries: LogEntry[];
  message: string;
}

// --- Dataset discovery and preview ---

export interface DatasetInfo {
  name: string;
  description: string;
  path: string;
  format: string;
  num_files: number;
}

export interface DatasetsListResponse {
  datasets_dir: string;
  datasets: DatasetInfo[];
}

export interface DatasetPreviewRequest {
  dataset_name: string;
  max_lines: number;
  start_line?: number;
}

export type LogLevel = "ERROR" | "WARN" | "WARNING" | "INFO" | "DEBUG" | "FATAL" | "CRITICAL" | "TRACE";

export const LOG_LEVEL_COLORS: Record<string, string> = {
  ERROR: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
  FATAL: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
  CRITICAL: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
  WARN: "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400",
  WARNING: "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400",
  INFO: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400",
  DEBUG: "bg-sky-100 text-sky-800 dark:bg-sky-900/30 dark:text-sky-400",
  TRACE: "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400",
};

export const CHART_COLORS = [
  "hsl(var(--chart-1))",
  "hsl(var(--chart-2))",
  "hsl(var(--chart-3))",
  "hsl(var(--chart-4))",
  "hsl(var(--chart-5))",
];

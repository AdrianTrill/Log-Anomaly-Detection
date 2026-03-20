// ---------------------------------------------------------------------------
// Shared constants, labels, and formatting for inference / anomaly detection UI
// ---------------------------------------------------------------------------

// Model display names (backend ID → human label)
const MODEL_DISPLAY_NAMES: Record<string, string> = {
  transformer_encoder: "Transformer Encoder",
};

export function formatModelName(raw: string | null): string {
  if (!raw) return "Not assigned";
  return MODEL_DISPLAY_NAMES[raw] ?? raw;
}

// Inference status labels
export const INFERENCE_STATUS_LABEL: Record<string, string> = {
  completed: "Completed",
  not_run: "Pending",
  not_available: "Unavailable",
  error: "Error",
};

// Prediction labels
export const PREDICTION_LABEL: Record<string, string> = {
  anomaly: "Anomaly",
  normal: "Normal",
};

// Prediction / anomaly score color tokens for Tailwind classes
export const ANOMALY_COLORS = {
  badge: "bg-red-500/15 text-red-600 dark:text-red-400",
  table: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
  text: "text-red-600 dark:text-red-400",
  subtleText: "text-red-600/70 dark:text-red-400/70",
} as const;

export const NORMAL_COLORS = {
  badge: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400",
  table: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400",
  text: "text-emerald-600 dark:text-emerald-400",
  subtleText: "text-muted-foreground/50",
} as const;

export function predictionColors(prediction: string | null) {
  return prediction === "anomaly" ? ANOMALY_COLORS : NORMAL_COLORS;
}

// Score formatting
export function formatScore(score: number): string {
  return (score * 100).toFixed(1);
}

export function isAnomalyScore(score: number): boolean {
  return score >= 0.5;
}

export function formatAnomalyRate(count: number, total: number): string {
  if (total === 0) return "0.0";
  return ((count / total) * 100).toFixed(1);
}

// Canonical scope note — defined once, used wherever the HDFS scope needs explanation
export const HDFS_SCOPE_NOTE =
  "Predictions are per HDFS block-session — all log lines in the same block share one anomaly score.";

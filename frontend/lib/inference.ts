// ---------------------------------------------------------------------------
// Shared constants, labels, and formatting for inference / anomaly detection UI
// ---------------------------------------------------------------------------

// Model display names (backend ID → human label)
const MODEL_DISPLAY_NAMES: Record<string, string> = {
  transformer_encoder: "Transformer Encoder",
  transformer_encoder_hdfs: "Transformer Encoder (HDFS)",
  transformer_encoder_bgl: "Transformer Encoder (BGL)",
  logbert_hdfs: "LogBERT (HDFS)",
  logbert_bgl: "LogBERT (BGL)",
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

// Scope notes — one per inference granularity
export const HDFS_SCOPE_NOTE =
  "Predictions are per HDFS block-session — all log lines in the same block share one anomaly score.";

export const BGL_SCOPE_NOTE =
  "Predictions are per sliding window — consecutive log lines in the same window share one anomaly score.";

const SCOPE_NOTES: Record<string, string> = {
  hdfs_block_session: HDFS_SCOPE_NOTE,
  bgl_sliding_window: BGL_SCOPE_NOTE,
};

export function getScopeNote(scope: string | null | undefined): string | null {
  if (!scope) return null;
  return SCOPE_NOTES[scope] ?? null;
}

// Short scope labels for metadata strip
const SCOPE_LABELS: Record<string, string> = {
  hdfs_block_session: "Block-session",
  bgl_sliding_window: "Sliding-window",
};

export function getScopeLabel(scope: string | null | undefined): string {
  if (!scope) return "Unknown";
  return SCOPE_LABELS[scope] ?? scope;
}

// Per-entry scope context for the detail panel "why flagged" helper
const SCOPE_CONTEXTS: Record<string, string> = {
  hdfs_block_session:
    "This line belongs to an HDFS block-session. All lines sharing the same block ID receive the same anomaly score from the model.",
  bgl_sliding_window:
    "This line is part of a 50-line sliding window. All lines in the same window share one anomaly score from the model.",
};

export function getScopeContext(modelName: string | null | undefined): string | null {
  if (!modelName) return null;
  if (modelName.includes("hdfs")) return SCOPE_CONTEXTS.hdfs_block_session;
  if (modelName.includes("bgl")) return SCOPE_CONTEXTS.bgl_sliding_window;
  return null;
}

export function formatThreshold(threshold: number | null | undefined): string {
  if (threshold == null) return "—";
  return threshold.toFixed(2);
}

// Derive default threshold from model name when backend value not available
export function getDefaultThreshold(modelName: string | null | undefined): number | null {
  if (!modelName) return null;
  if (modelName.includes("bgl")) return 0.8;
  if (modelName.includes("hdfs")) return 0.5;
  return null;
}

// Model name without dataset suffix — "Transformer Encoder (HDFS)" → "Transformer Encoder"
export function shortModelLabel(modelId: string): string {
  return formatModelName(modelId).replace(/\s*\(.*?\)/, "");
}

// Compact column header — "transformer_encoder_hdfs" → "TE", "logbert_bgl" → "LogBERT"
export function columnModelLabel(modelId: string): string {
  if (modelId.startsWith("transformer_encoder")) return "TE";
  if (modelId.startsWith("logbert")) return "LogBERT";
  return shortModelLabel(modelId);
}

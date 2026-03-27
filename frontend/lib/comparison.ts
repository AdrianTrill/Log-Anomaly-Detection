import type { LogEntry, ComparisonEntry } from "@/types/log";

export function mergeComparisonEntries(
  entriesA: LogEntry[],
  entriesB: LogEntry[],
): ComparisonEntry[] {
  return entriesA.map((a, i) => {
    const b = entriesB[i] ?? a;
    return {
      base: {
        ...a,
        anomaly_score: null,
        prediction: null,
        model_name: null,
        inference_status: "not_run" as const,
      },
      modelA: {
        model_name: a.model_name ?? "",
        anomaly_score: a.anomaly_score,
        prediction: a.prediction,
      },
      modelB: {
        model_name: b.model_name ?? "",
        anomaly_score: b.anomaly_score,
        prediction: b.prediction,
      },
    };
  });
}

export interface AgreementStats {
  bothAnomaly: number;
  onlyA: number;
  onlyB: number;
  bothNormal: number;
  total: number;
}

export function computeAgreement(entries: ComparisonEntry[]): AgreementStats {
  let bothAnomaly = 0;
  let onlyA = 0;
  let onlyB = 0;
  let bothNormal = 0;

  for (const e of entries) {
    const aAnom = e.modelA.prediction === "anomaly";
    const bAnom = e.modelB.prediction === "anomaly";
    if (aAnom && bAnom) bothAnomaly++;
    else if (aAnom) onlyA++;
    else if (bAnom) onlyB++;
    else bothNormal++;
  }

  return { bothAnomaly, onlyA, onlyB, bothNormal, total: entries.length };
}

export type ComparisonFilter = "all" | "any_anomaly" | "both_anomaly" | "disagree";

export function filterComparisonEntries(
  entries: ComparisonEntry[],
  filter: ComparisonFilter,
): ComparisonEntry[] {
  if (filter === "all") return entries;
  return entries.filter((e) => {
    const aAnom = e.modelA.prediction === "anomaly";
    const bAnom = e.modelB.prediction === "anomaly";
    switch (filter) {
      case "any_anomaly":
        return aAnom || bAnom;
      case "both_anomaly":
        return aAnom && bAnom;
      case "disagree":
        return aAnom !== bAnom;
      default:
        return true;
    }
  });
}

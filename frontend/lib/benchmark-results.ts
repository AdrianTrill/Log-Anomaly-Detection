export interface BenchmarkResultSummary {
  id: string;
  dataset: "HDFS" | "BGL";
  modelLabel: string;
  f1: number;
  precision: number;
  recall: number;
  rocAuc: number;
  threshold: number;
  tp: number;
  fp: number;
  fn: number;
  tn: number;
}

export const BENCHMARK_RESULTS: BenchmarkResultSummary[] = [
  {
    id: "transformer_encoder_hdfs",
    dataset: "HDFS",
    modelLabel: "Transformer Encoder",
    f1: 99.35,
    precision: 98.77,
    recall: 99.94,
    rocAuc: 99.99,
    threshold: 0.5,
    tp: 1683,
    fp: 21,
    fn: 1,
    tn: 55802,
  },
  {
    id: "logbert_hdfs",
    dataset: "HDFS",
    modelLabel: "LogBERT",
    f1: 99.56,
    precision: 99.12,
    recall: 100.0,
    rocAuc: 99.99,
    threshold: 0.5,
    tp: 1684,
    fp: 15,
    fn: 0,
    tn: 55808,
  },
  {
    id: "transformer_encoder_bgl",
    dataset: "BGL",
    modelLabel: "Transformer Encoder",
    f1: 93.85,
    precision: 97.90,
    recall: 90.11,
    rocAuc: 99.78,
    threshold: 0.8,
    tp: 793,
    fp: 17,
    fn: 87,
    tn: 8530,
  },
  {
    id: "logbert_bgl",
    dataset: "BGL",
    modelLabel: "LogBERT",
    f1: 94.49,
    precision: 98.64,
    recall: 90.68,
    rocAuc: 99.81,
    threshold: 0.8,
    tp: 798,
    fp: 11,
    fn: 82,
    tn: 8536,
  },
];

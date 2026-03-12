import {
  UploadResponse,
  HealthResponse,
  DatasetsListResponse,
  DatasetPreviewRequest,
} from "@/types/log";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

export async function uploadLogFile(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_URL}/api/upload`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: "Upload failed" }));
    throw new ApiError(res.status, body.detail || "Upload failed");
  }

  return res.json();
}

export async function checkHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_URL}/api/health`);
  if (!res.ok) {
    throw new ApiError(res.status, "Health check failed");
  }
  return res.json();
}

export async function fetchDatasets(): Promise<DatasetsListResponse> {
  const res = await fetch(`${API_URL}/api/datasets`);
  if (!res.ok) {
    throw new ApiError(res.status, "Failed to fetch datasets");
  }
  return res.json();
}

export async function previewDataset(request: DatasetPreviewRequest): Promise<UploadResponse> {
  const res = await fetch(`${API_URL}/api/datasets/preview`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: "Dataset preview failed" }));
    throw new ApiError(res.status, body.detail || "Dataset preview failed");
  }
  return res.json();
}

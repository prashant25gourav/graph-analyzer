export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export type HealthResponse = {
  status: string;
  service: string;
  version: string;
};

export type ApiResult = Record<string, unknown>;

async function parseApiError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as {
      detail?: { error_code?: string; message?: string; details?: string };
    };

    if (body.detail?.message) {
      const extra = body.detail.details ? ` (${body.detail.details})` : "";
      return `${body.detail.message}${extra}`;
    }
  } catch {
    // Use fallback when response cannot be parsed.
  }

  return `Request failed with status ${response.status}`;
}

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/api/health`);

  if (!response.ok) {
    throw new Error(`Health check failed with status ${response.status}`);
  }

  return response.json() as Promise<HealthResponse>;
}

export async function uploadForAnalyze(file: File): Promise<ApiResult> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/v1/analyze`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(await parseApiError(response));
  }

  return response.json() as Promise<ApiResult>;
}

export async function uploadForCompare(graphA: File, graphB: File): Promise<ApiResult> {
  const formData = new FormData();
  formData.append("graph_a", graphA);
  formData.append("graph_b", graphB);

  const response = await fetch(`${API_BASE_URL}/api/v1/compare`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(await parseApiError(response));
  }

  return response.json() as Promise<ApiResult>;
}

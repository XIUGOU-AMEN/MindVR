import type { AnalysisResult, HealthInfo } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

async function parse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = `请求失败 (${response.status})`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      detail = `${detail} ${await response.text()}`;
    }
    throw new Error(detail);
  }
  return (await response.json()) as T;
}

export async function analyzeText(
  transcript: string,
  participantId = "anonymous"
): Promise<AnalysisResult> {
  const form = new FormData();
  form.append("transcript", transcript);
  form.append("participant_id", participantId);
  const response = await fetch(`${API_BASE}/api/v1/analyze`, { method: "POST", body: form });
  return parse<AnalysisResult>(response);
}

export async function analyzeAudio(
  file: File,
  participantId = "anonymous"
): Promise<AnalysisResult> {
  const form = new FormData();
  form.append("audio", file);
  form.append("participant_id", participantId);
  const response = await fetch(`${API_BASE}/api/v1/analyze`, { method: "POST", body: form });
  return parse<AnalysisResult>(response);
}

export async function runDemo(): Promise<AnalysisResult> {
  const response = await fetch(`${API_BASE}/api/v1/demo`, { method: "POST" });
  return parse<AnalysisResult>(response);
}

export async function fetchHealth(): Promise<HealthInfo> {
  const response = await fetch(`${API_BASE}/api/v1/health`);
  return parse<HealthInfo>(response);
}
export type RiskLevel = "normal" | "mild" | "moderate" | "severe";

export interface EvidenceItem {
  feature: string;
  label_zh: string;
  value: number;
  contribution: number;
  direction: "up" | "down";
}

export interface AnalysisResult {
  participant_id: string;
  phq8_score_estimation: number;
  depression_probability: number;
  depression_classification: number;
  risk_level: RiskLevel;
  evidence: EvidenceItem[];
  transcript_excerpt: string;
  model_version: string;
  llm_backend: string;
  latency_ms: number;
}

export interface HealthInfo {
  status: string;
  version: string;
  llm_backend: string;
  model_loaded: boolean;
  asr_enabled: boolean;
}

export const RISK_META: Record<RiskLevel, { label: string; color: string; hint: string }> = {
  normal: { label: "无明显抑郁风险", color: "#2fbf71", hint: "保持规律作息与社交活动" },
  mild: { label: "轻度风险", color: "#e0b32c", hint: "建议关注睡眠与情绪波动" },
  moderate: { label: "中度风险", color: "#e07b39", hint: "建议寻求专业心理评估" },
  severe: { label: "重度风险", color: "#d64b4b", hint: "建议尽快联系专业机构" },
};
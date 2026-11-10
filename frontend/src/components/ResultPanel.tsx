import { RISK_META } from "../types";
import type { AnalysisResult } from "../types";

interface Props {
  result: AnalysisResult | null;
  loading: boolean;
  onEnterVR: () => void;
}

export default function ResultPanel({ result, loading, onEnterVR }: Props) {
  if (!result) {
    return (
      <section className="card">
        <h2>感知结果</h2>
        <p className="card-hint">提交访谈后，这里会展示 PHQ-8 分数、风险等级与可解释依据。</p>
        <div className="empty">
          <span>{loading ? "正在分析…" : "尚无结果"}</span>
          <span>结果仅用于研究演示，不构成诊断</span>
        </div>
      </section>
    );
  }

  const meta = RISK_META[result.risk_level];
  const maxContribution = Math.max(
    ...result.evidence.map((item) => Math.abs(item.contribution)),
    0.001
  );

  return (
    <section className="card">
      <h2>感知结果</h2>
      <p className="card-hint">模型输出 PHQ-8 分数估计与抑郁风险概率</p>

      <div className="score-row">
        <span className="score" style={{ color: meta.color }}>
          {result.phq8_score_estimation.toFixed(1)}
        </span>
        <span className="score-unit">/ 24 · PHQ-8</span>
      </div>

      <div
        className="risk-badge"
        style={{ background: `${meta.color}1f`, color: meta.color, border: `1px solid ${meta.color}55` }}
      >
        {meta.label}
      </div>

      <div className="prob-track">
        <div className="prob-fill" style={{ width: `${result.depression_probability * 100}%` }} />
      </div>
      <div className="meta-grid">
        <span>
          模型风险概率 <strong>{(result.depression_probability * 100).toFixed(1)}%</strong>
        </span>
        <span>
          分类 <strong>{result.depression_classification === 1 ? "抑郁" : "非抑郁"}</strong>
        </span>
        <span>
          建议 <strong>{meta.hint}</strong>
        </span>
        <span>
          耗时 <strong>{result.latency_ms} ms</strong>
        </span>
        <span>
          模型 <strong>{result.model_version}</strong>
        </span>
        <span>
          LLM <strong>{result.llm_backend}</strong>
        </span>
      </div>

      {result.evidence.length > 0 && (
        <>
          <p className="evidence-title">主要依据（近似归因，非临床解释）</p>
          <ul className="evidence-list">
            {result.evidence.map((item) => {
              const ratio = Math.abs(item.contribution) / maxContribution;
              const color = item.direction === "up" ? "#d64b4b" : "#2fbf71";
              return (
                <li className="evidence-item" key={item.feature}>
                  <span>{item.label_zh}</span>
                  <span className="evidence-bar">
                    <span style={{ width: `${Math.max(ratio * 100, 6)}%`, background: color }} />
                  </span>
                  <span className="value">{item.value.toFixed(2)}</span>
                </li>
              );
            })}
          </ul>
        </>
      )}

      {result.transcript_excerpt && <div className="excerpt">“{result.transcript_excerpt}…”</div>}

      <div className="actions" style={{ marginTop: 18 }}>
        <button className="btn-primary" onClick={onEnterVR}>
          进入沉浸式场景
        </button>
      </div>
    </section>
  );
}
import { useEffect, useState } from "react";
import { analyzeAudio, analyzeText, fetchHealth, runDemo } from "./api";
import type { AnalysisResult } from "./types";
import ResultPanel from "./components/ResultPanel";
import UploadPanel from "./components/UploadPanel";
import VRStage from "./components/VRStage";

export default function App() {
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [immersive, setImmersive] = useState(false);
  const [backend, setBackend] = useState("checking");
  const [modelReady, setModelReady] = useState(false);
  const [asrEnabled, setAsrEnabled] = useState(false);

  useEffect(() => {
    fetchHealth()
      .then((health) => {
        setBackend(health.llm_backend);
        setModelReady(health.model_loaded);
        setAsrEnabled(health.asr_enabled);
      })
      .catch(() => setBackend("offline"));
  }, []);

  async function run(task: () => Promise<AnalysisResult>) {
    setLoading(true);
    setError("");
    try {
      setResult(await task());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  if (immersive) {
    return <VRStage result={result} onExit={() => setImmersive(false)} />;
  }

  return (
    <div className="app">
      <header className="hero">
        <div>
          <p className="eyebrow">Multimodal Perception × VR</p>
          <h1>MindVR</h1>
          <p className="subtitle">
            基于访谈文本与多模态特征的抑郁风险感知演示。结果仅用于学术研究，不构成医学诊断。
          </p>
        </div>
        <div className="status">
          <span className={`dot ${modelReady ? "ok" : "warn"}`} />
          <span>模型 {modelReady ? "已加载" : "未加载"}</span>
          <span className="divider" />
          <span>LLM 后端 {backend}</span>
        </div>
      </header>

      <main className="layout">
        <UploadPanel
          loading={loading}
          error={error}
          asrEnabled={asrEnabled}
          onText={(text, participantId) => run(() => analyzeText(text, participantId))}
          onAudio={(file, participantId) => run(() => analyzeAudio(file, participantId))}
          onDemo={() => run(runDemo)}
        />
        <ResultPanel result={result} loading={loading} onEnterVR={() => setImmersive(true)} />
      </main>

      <footer className="footer">
        <span>MindVR · 开源学术项目</span>
        <span>数据合规：仓库不含任何 DAIC-WOZ 原始数据</span>
      </footer>
    </div>
  );
}
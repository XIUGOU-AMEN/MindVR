import { useRef, useState } from "react";

interface Props {
  loading: boolean;
  error: string;
  asrEnabled: boolean;
  onText: (transcript: string, participantId: string) => void;
  onAudio: (file: File, participantId: string) => void;
  onDemo: () => void;
}

export default function UploadPanel({
  loading,
  error,
  asrEnabled,
  onText,
  onAudio,
  onDemo,
}: Props) {
  const [transcript, setTranscript] = useState("");
  const [participantId, setParticipantId] = useState("anonymous");
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const isTranscriptFile = audioFile ? /\.(csv|tsv)$/i.test(audioFile.name) : false;
  const blockedAudio = Boolean(audioFile && !isTranscriptFile && !asrEnabled);

  return (
    <section className="card">
      <h2>输入访谈</h2>
      <p className="card-hint">
        粘贴访谈转写文本，或上传 DAIC 逐句转写 CSV。音频分析需开启华为云 SIS 转写，
        未开启时请使用 CSV。没有数据时可直接运行内置示例。
      </p>

      <div className="field">
        <label htmlFor="pid">参与者标识（仅用于本地记录，可随意填写）</label>
        <input
          id="pid"
          type="text"
          value={participantId}
          onChange={(event) => setParticipantId(event.target.value)}
          placeholder="anonymous"
        />
      </div>

      <div className="field">
        <label htmlFor="transcript">访谈转写文本</label>
        <textarea
          id="transcript"
          value={transcript}
          onChange={(event) => setTranscript(event.target.value)}
          placeholder="例如：最近一直睡不好，以前喜欢的事情现在也没兴趣了……"
        />
      </div>

      <div className="field">
        <label htmlFor="audio">或上传音频 / DAIC 转写 CSV</label>
        <input
          id="audio"
          ref={fileRef}
          type="file"
          accept="audio/*,.csv,.tsv"
          onChange={(event) => setAudioFile(event.target.files?.[0] ?? null)}
        />
      </div>

      <div className="actions">
        <button
          className="btn-primary"
          disabled={loading || !transcript.trim()}
          onClick={() => onText(transcript, participantId)}
        >
          {loading ? "分析中…" : "分析文本"}
        </button>
        <button
          className="btn-ghost"
          disabled={loading || !audioFile || blockedAudio}
          onClick={() => audioFile && !blockedAudio && onAudio(audioFile, participantId)}
        >
          分析文件
        </button>
        <button className="btn-ghost" disabled={loading} onClick={onDemo}>
          运行示例
        </button>
      </div>

      {blockedAudio && (
        <div className="alert">
          当前未开启云端语音识别（USE_CLOUD_ASR=false），音频无法直接分析。
          请改选同一 participant 目录下的 <code>_Transcript.csv</code>。
        </div>
      )}

      {error && <div className="alert">{error}</div>}
    </section>
  );
}
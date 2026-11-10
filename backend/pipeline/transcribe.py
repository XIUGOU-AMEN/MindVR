"""语音转写。

两条路径：
1. 上传 DAIC 转写 CSV：直接解析（默认演示方式，零成本）。
2. 上传音频：调用华为云 SIS 短语音识别。长访谈会自动按 55 秒切片、逐段识别后拼接。

SIS 短语音接口对单段音频有时长限制，因此这里用标准库 wave 做切片，不依赖 ffmpeg。
华为云 SDK 放在 requirements-cloud.txt 中，未安装时模块仍可正常导入。
"""

from __future__ import annotations

import base64
import csv
import io
import time
import wave
from dataclasses import dataclass
from typing import Protocol

from backend.config import get_settings

TEXT_COLUMNS = ("text", "value", "transcript", "utterance")
START_COLUMNS = ("start_time", "starttime", "start", "begin")
SPEAKER_COLUMNS = ("speaker", "role", "participant")

SUPPORTED_SAMPLE_RATES = (8000, 16000)


@dataclass
class AudioInfo:
    channels: int
    sample_width: int
    frame_rate: int
    frames: int
    duration: float

    def as_dict(self) -> dict:
        return {
            "channels": self.channels,
            "sample_width": self.sample_width,
            "frame_rate": self.frame_rate,
            "frames": self.frames,
            "duration": round(self.duration, 2),
        }


def inspect_wav(data: bytes) -> AudioInfo:
    """读取 wav 头信息，非 wav 或损坏文件会抛 ValueError。"""
    try:
        with wave.open(io.BytesIO(data), "rb") as source:
            channels = source.getnchannels()
            sample_width = source.getsampwidth()
            frame_rate = source.getframerate()
            frames = source.getnframes()
    except (wave.Error, EOFError) as exc:
        raise ValueError(f"无法解析 wav 文件：{exc}") from exc

    duration = frames / frame_rate if frame_rate else 0.0
    return AudioInfo(
        channels=channels,
        sample_width=sample_width,
        frame_rate=frame_rate,
        frames=frames,
        duration=duration,
    )


def split_wav(data: bytes, max_seconds: float = 55.0) -> list[bytes]:
    """把 wav 切成不超过 max_seconds 的若干段，返回每段的完整 wav 字节。"""
    info = inspect_wav(data)
    frames_per_chunk = max(1, int(info.frame_rate * max_seconds))
    chunks: list[bytes] = []

    with wave.open(io.BytesIO(data), "rb") as source:
        while True:
            frames = source.readframes(frames_per_chunk)
            if not frames:
                break
            buffer = io.BytesIO()
            with wave.open(buffer, "wb") as target:
                target.setnchannels(info.channels)
                target.setsampwidth(info.sample_width)
                target.setframerate(info.frame_rate)
                target.writeframes(frames)
            chunks.append(buffer.getvalue())

    return chunks


class Transcriber(Protocol):
    def transcribe(self, audio_bytes: bytes) -> str: ...


class PassthroughTranscriber:
    """未开启云端识别时的占位实现，保证接口不崩、返回空文本。"""

    name = "passthrough"

    def transcribe(self, audio_bytes: bytes) -> str:
        return ""


class SisTranscriber:
    """华为云 SIS 短语音识别（一句话识别）。

    流程：校验采样率 -> 按 55 秒切片 -> 逐段调用 -> 拼接文本。
    每段失败会重试一次，仍失败则跳过，不中断整段访谈。
    """

    name = "huawei-sis"

    def __init__(self) -> None:
        settings = get_settings()
        self.ak = settings.huawei_ak
        self.sk = settings.huawei_sk
        self.project_id = settings.huawei_project_id
        self.region = settings.huawei_region
        self.max_seconds = settings.sis_asr_max_seconds
        self.property = settings.sis_asr_property
        self.last_chunks = 0
        self.last_failed = 0

    def _build_client(self):
        try:
            from huaweicloudsdkcore.auth.credentials import BasicCredentials
            from huaweicloudsdksis.v1.region.sis_region import SisRegion
            from huaweicloudsdksis.v1.sis_client import SisClient
        except ImportError as exc:
            raise RuntimeError(
                "未安装华为云 SIS SDK，请执行 pip install -r requirements-cloud.txt"
            ) from exc

        if not self.ak or not self.sk or not self.project_id:
            raise RuntimeError(
                "缺少华为云凭据：请在 .env 填写 HUAWEI_AK / HUAWEI_SK / HUAWEI_PROJECT_ID"
            )

        credentials = BasicCredentials(self.ak, self.sk, self.project_id)
        return (
            SisClient.new_builder()
            .with_credentials(credentials)
            .with_region(SisRegion.value_of(self.region))
            .build()
        )

    def _recognize_chunk(self, client, chunk: bytes) -> str:
        try:
            from huaweicloudsdksis.v1 import Config, PostShortAudioReq, RecognizeShortAudioRequest
        except ImportError as exc:
            raise RuntimeError("SIS SDK 导入失败，请检查 requirements-cloud.txt") from exc

        body = PostShortAudioReq(
            config=Config(audio_format="wav", property=self.property),
            data=base64.b64encode(chunk).decode("utf-8"),
        )
        request = RecognizeShortAudioRequest(body=body)
        response = client.recognize_short_audio(request)
        result = getattr(response, "result", None)
        return getattr(result, "text", "") or ""

    def transcribe(self, audio_bytes: bytes) -> str:
        info = inspect_wav(audio_bytes)
        if info.frame_rate not in SUPPORTED_SAMPLE_RATES:
            raise RuntimeError(
                f"当前 wav 采样率为 {info.frame_rate} Hz，SIS 短语音仅支持 8000/16000 Hz。"
                "请先转换为 16k 单声道，例如："
                "ffmpeg -i input.wav -ar 16000 -ac 1 output.wav"
            )

        chunks = split_wav(audio_bytes, self.max_seconds)
        self.last_chunks = len(chunks)
        self.last_failed = 0
        if not chunks:
            return ""

        client = self._build_client()
        texts: list[str] = []

        for chunk in chunks:
            text = ""
            for attempt in range(2):
                try:
                    text = self._recognize_chunk(client, chunk)
                    break
                except Exception:
                    if attempt == 1:
                        self.last_failed += 1
                    else:
                        time.sleep(0.4)
            if text:
                texts.append(text.strip())
            time.sleep(0.08)

        return "".join(texts)


def _decode(data: bytes | str) -> str:
    if isinstance(data, str):
        return data
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="ignore")


def _detect_delimiter(sample: str) -> str:
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;")
        return dialect.delimiter
    except csv.Error:
        return "," if sample.count(",") >= sample.count("\t") else "\t"


def _match_column(normalized: dict[str, str], candidates: tuple[str, ...]) -> str | None:
    for candidate in candidates:
        if candidate in normalized:
            return normalized[candidate]
    for key, original in normalized.items():
        for candidate in candidates:
            if candidate in key:
                return original
    return None


def parse_daic_transcript(data: bytes | str) -> str:
    """把 DAIC-WOZ 的逐句转写表解析为一段连续文本。

    兼容两种常见列名：
    - 官方版：start_time / stop_time / speaker / value
    - 预处理版：Start_Time / End_Time / Text / Confidence

    若存在 speaker 列，只保留 Participant 的发言；按开始时间排序后拼接。
    """
    content = _decode(data)
    if not content.strip():
        return ""

    if not any(char in content[:4096] for char in ",\t;"):
        return " ".join(content.split())

    delimiter = _detect_delimiter(content[:4096])
    reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
    if not reader.fieldnames:
        return " ".join(content.split())

    normalized = {
        str(name).strip().lower().replace(" ", "_"): name
        for name in reader.fieldnames
        if name is not None
    }
    text_key = _match_column(normalized, TEXT_COLUMNS)
    if text_key is None:
        return " ".join(content.split())

    start_key = _match_column(normalized, START_COLUMNS)
    speaker_key = _match_column(normalized, SPEAKER_COLUMNS)

    rows: list[tuple[float, str]] = []
    for index, row in enumerate(reader):
        value = (row.get(text_key) or "").strip()
        if not value:
            continue
        if speaker_key:
            speaker = (row.get(speaker_key) or "").strip().lower()
            if speaker and "participant" not in speaker:
                continue
        try:
            order = float(row.get(start_key) or index)
        except (TypeError, ValueError):
            order = float(index)
        rows.append((order, value))

    rows.sort(key=lambda item: item[0])
    return "\n".join(item[1] for item in rows).strip()


def looks_like_transcript_file(filename: str) -> bool:
    name = (filename or "").lower()
    return name.endswith(".csv") or name.endswith(".tsv")


def looks_like_transcript_content(text: str) -> bool:
    """判断一段粘贴文本是不是整份转写表，而不是访谈正文。"""
    head = (text or "")[:2048].lower()
    has_time = "start_time" in head or "starttime" in head or "start time" in head
    has_text = ",text" in head or "\ttext" in head or ",value" in head or "\tvalue" in head
    return has_time and has_text


def get_transcriber() -> Transcriber:
    settings = get_settings()
    if settings.use_cloud_asr:
        return SisTranscriber()
    return PassthroughTranscriber()
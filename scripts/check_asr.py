"""本地检查 ASR 链路（不经过 HTTP）。

用法：
    # 按编号自动查找 wav（推荐，无需手拼路径）
    python scripts/check_asr.py --participant 300

    # 指定完整路径
    python scripts/check_asr.py --file "E:/Create/daic_woz_data/300_P/300_AUDIO.wav"

    # 真实调用华为云 SIS（会消耗音频时长额度）
    python scripts/check_asr.py --participant 300 --call
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import get_settings  # noqa: E402
from backend.pipeline.transcribe import get_transcriber, inspect_wav, split_wav  # noqa: E402

DEFAULT_ROOT = Path("E:/Create/daic_woz_data")


def find_audio(root: Path, participant: str) -> Path | None:
    patterns = [
        f"{participant}_P/*_AUDIO.wav",
        f"*{participant}*_AUDIO.wav",
        f"*{participant}*.wav",
    ]
    for pattern in patterns:
        for candidate in root.rglob(pattern):
            if candidate.is_file():
                return candidate
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=Path, default=None, help="wav 完整路径")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="数据集根目录")
    parser.add_argument("--participant", default=None, help="参与者编号，如 300")
    parser.add_argument("--call", action="store_true", help="真实调用 SIS")
    parser.add_argument("--seconds", type=float, default=None, help="切片长度，默认读 .env")
    args = parser.parse_args()

    if args.file is None:
        if not args.participant:
            raise SystemExit("请指定 --file 或 --participant，例如：--participant 300")
        if not args.root.exists():
            raise SystemExit(f"数据集目录不存在: {args.root}")
        found = find_audio(args.root, args.participant)
        if found is None:
            raise SystemExit(f"在 {args.root} 下没有找到 {args.participant} 的 wav")
        args.file = found

    if not args.file.exists():
        raise SystemExit(f"文件不存在: {args.file}")

    data = args.file.read_bytes()
    try:
        info = inspect_wav(data)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    settings = get_settings()
    max_seconds = args.seconds or settings.sis_asr_max_seconds
    chunks = split_wav(data, max_seconds)

    print("=" * 62)
    print(f"文件: {args.file}")
    print(f"格式: {info.as_dict()}")
    print(f"时长: {info.duration:.1f} 秒")
    print(f"切片: {len(chunks)} 段（每段 ≤ {max_seconds:.0f} 秒）")
    print(f"采样率支持: {'是' if info.frame_rate in (8000, 16000) else '否'}")
    print(f"USE_CLOUD_ASR: {settings.use_cloud_asr}")
    print(f"SIS_PROPERTY: {settings.sis_asr_property}")
    print("=" * 62)

    if info.frame_rate not in (8000, 16000):
        print("SIS 短语音仅支持 8000/16000 Hz。请先转换：")
        print("  ffmpeg -i input.wav -ar 16000 -ac 1 output.wav")
        return

    if not args.call:
        print("未加 --call，仅检查格式与切片，不消耗额度。")
        return

    transcriber = get_transcriber()
    print(f"转写后端: {transcriber.name}")
    if transcriber.name != "huawei-sis":
        print("USE_CLOUD_ASR=false，请在 .env 改为 true 并填写 AK/SK/ProjectId。")
        return

    try:
        text = transcriber.transcribe(data)
    except RuntimeError as exc:
        raise SystemExit(f"转写失败: {exc}") from exc

    print("-" * 62)
    print(f"分段数: {getattr(transcriber, 'last_chunks', 0)}")
    print(f"失败段数: {getattr(transcriber, 'last_failed', 0)}")
    print(f"文本长度: {len(text)} 字")
    print(text[:800])
    print("-" * 62)


if __name__ == "__main__":
    main()
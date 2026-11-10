import io
import wave

import pytest

from backend.pipeline.transcribe import (
    inspect_wav,
    looks_like_transcript_file,
    parse_daic_transcript,
    split_wav,
)

OFFICIAL_FORMAT = (
    "start_time\tstop_time\tspeaker\tvalue\n"
    "0.0\t5.0\tEllie\tHi, I am Ellie.\n"
    "5.5\t9.0\tParticipant\tI feel tired all the time.\n"
    "9.5\t12.0\tEllie\tTell me more.\n"
    "12.5\t18.0\tParticipant\tI have no interest in anything.\n"
)

PREPROCESSED_FORMAT = (
    "Start_Time,End_Time,Text,Confidence\n"
    "14.3,15.1,so I'm going to,0.93\n"
    "20.3,21.1,interview in Spanish,0.60\n"
    "23.9,24.3,okay,0.69\n"
)


def make_wav(seconds: float, rate: int = 16000) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(rate)
        target.writeframes(b"\x00\x00" * int(rate * seconds))
    return buffer.getvalue()


def test_parse_official_format_filters_ellie() -> None:
    text = parse_daic_transcript(OFFICIAL_FORMAT)
    assert "I feel tired all the time." in text
    assert "I have no interest in anything." in text
    assert "Hi, I am Ellie." not in text
    assert "Tell me more." not in text


def test_parse_preprocessed_format_sorts_by_time() -> None:
    text = parse_daic_transcript(PREPROCESSED_FORMAT)
    assert text.startswith("so I'm going to")
    assert "interview in Spanish" in text
    assert text.endswith("okay")


def test_parse_preserves_sentence_boundaries() -> None:
    text = parse_daic_transcript(PREPROCESSED_FORMAT)
    assert "\n" in text
    assert len(text.splitlines()) == 3


def test_parse_handles_bytes_and_bom() -> None:
    data = ("\ufeff" + PREPROCESSED_FORMAT).encode("utf-8")
    text = parse_daic_transcript(data)
    assert "interview in Spanish" in text


def test_parse_plain_text_passthrough() -> None:
    assert parse_daic_transcript("I feel very low today.") == "I feel very low today."


def test_parse_empty_returns_empty() -> None:
    assert parse_daic_transcript("") == ""
    assert parse_daic_transcript(b"") == ""


def test_transcript_file_detection() -> None:
    assert looks_like_transcript_file("300_Transcript.csv")
    assert looks_like_transcript_file("300_TRANSCRIPT.TSV")
    assert not looks_like_transcript_file("300_AUDIO.wav")


def test_english_interview_hits_cues() -> None:
    from backend.pipeline.features import extract_text_features

    text = (
        "I can't sleep at night. I have no interest in anything anymore. "
        "I feel tired all the time and I can't focus. I'm worthless."
    )
    features = extract_text_features(text)

    assert features["sleep_mention"] > 0
    assert features["anhedonia_mention"] > 0
    assert features["fatigue_mention"] > 0
    assert features["concentration_mention"] > 0
    assert features["worthlessness_mention"] > 0
    assert features["self_negation_ratio"] > 0
    assert features["first_person_ratio"] > 0


def test_inspect_wav_reads_metadata() -> None:
    info = inspect_wav(make_wav(2))
    assert info.frame_rate == 16000
    assert info.channels == 1
    assert info.duration == pytest.approx(2.0, abs=0.02)


def test_split_wav_into_chunks() -> None:
    data = make_wav(130)
    chunks = split_wav(data, 55)
    assert len(chunks) == 3
    for chunk in chunks:
        assert inspect_wav(chunk).duration <= 55.02


def test_split_wav_short_file() -> None:
    chunks = split_wav(make_wav(10), 55)
    assert len(chunks) == 1


def test_inspect_rejects_non_wav() -> None:
    with pytest.raises(ValueError):
        inspect_wav(b"not a wav file")
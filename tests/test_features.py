import numpy as np

from backend.pipeline.features import (
    DEFAULT_VALUES,
    FEATURE_NAMES,
    extract_text_features,
    merge_features,
    to_vector,
)


def test_empty_transcript_returns_empty_features() -> None:
    assert extract_text_features("") == {}
    assert extract_text_features("   ") == {}


def test_symptom_text_hits_cues() -> None:
    text = "最近一直失眠，什么都不想做，很累，注意力也集中不了，吃不下饭。"
    features = extract_text_features(text)
    assert features["sleep_mention"] > 0
    assert features["anhedonia_mention"] > 0
    assert features["fatigue_mention"] > 0
    assert features["concentration_mention"] > 0
    assert features["appetite_mention"] > 0
    assert features["word_count"] > 0


def test_merge_features_fills_defaults() -> None:
    merged = merge_features({"sleep_mention": 0.5})
    assert set(merged.keys()) == set(FEATURE_NAMES)
    assert merged["sleep_mention"] == 0.5
    assert merged["f0_mean"] == DEFAULT_VALUES["f0_mean"]


def test_vector_shape_matches_schema() -> None:
    vector = to_vector(merge_features({}))
    assert vector.shape == (1, len(FEATURE_NAMES))
    assert np.all(np.isfinite(vector))

def test_english_negation_is_not_counted() -> None:
    features = extract_text_features("I am not sad. I am not tired. I don't have insomnia.")
    assert features["neg_sentiment_ratio"] == 0.0
    assert features["fatigue_mention"] == 0.0
    assert features["sleep_mention"] == 0.0


def test_chinese_negation_is_not_counted() -> None:
    features = extract_text_features("我并不难过，也没有失眠，不觉得累。")
    assert features["neg_sentiment_ratio"] == 0.0
    assert features["sleep_mention"] == 0.0
    assert features["fatigue_mention"] == 0.0


def test_affirmed_negatives_are_still_counted() -> None:
    features = extract_text_features("I feel sad and tired, and I can't sleep.")
    assert features["neg_sentiment_ratio"] > 0
    assert features["fatigue_mention"] > 0
    assert features["sleep_mention"] > 0

"""Unit tests for the OpenAI client's response parsing (no network)."""

import pytest

from app.clients.ai_client import OpenAIClient
from app.errors import AIServiceError
from app.models.article import Sentiment


def test_parse_valid_json():
    result = OpenAIClient._parse(
        '{"summary": "A calm week.", "sentiment": "neutral", "sentiment_score": 0.0}'
    )
    assert result.summary == "A calm week."
    assert result.sentiment == Sentiment.neutral
    assert result.sentiment_score == 0.0


def test_parse_malformed_json_raises():
    with pytest.raises(AIServiceError):
        OpenAIClient._parse("not json")


def test_parse_bad_sentiment_raises():
    with pytest.raises(AIServiceError):
        OpenAIClient._parse('{"summary": "x", "sentiment": "great", "sentiment_score": 0.0}')


def test_parse_out_of_range_score_raises():
    with pytest.raises(AIServiceError):
        OpenAIClient._parse('{"summary": "x", "sentiment": "positive", "sentiment_score": 5}')


def test_parse_allows_mild_sign_disagreement():
    # A positive label with a slightly negative score is benign and kept.
    result = OpenAIClient._parse(
        '{"summary": "x", "sentiment": "positive", "sentiment_score": -0.05}'
    )
    assert result.sentiment == Sentiment.positive
    assert result.sentiment_score == -0.05


def test_parse_rejects_gross_sign_contradiction():
    with pytest.raises(AIServiceError):
        OpenAIClient._parse(
            '{"summary": "x", "sentiment": "positive", "sentiment_score": -0.9}'
        )

"""Contract checks for the minimal A2A message envelope used by the lab."""

from __future__ import annotations

import pytest

pytest.importorskip("a2a_otel_kit")

from agent_runtime_boundaries.adapters.a2a_transport import _extract_text


def test_extract_text_accepts_v1_message_shape() -> None:
    assert _extract_text({"parts": [{"text": "result"}]}) == "result"


def test_extract_text_accepts_message_wrapper() -> None:
    assert _extract_text({"message": {"parts": [{"text": "result"}]}}) == "result"


def test_extract_text_rejects_missing_content() -> None:
    with pytest.raises(RuntimeError, match="text result"):
        _extract_text({"parts": []})

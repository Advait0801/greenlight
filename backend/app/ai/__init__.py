"""Claude API access. Only intake and drafting services may import this package; the rule engine,
deadline calculator and year planner must never do so (tests/unit/test_architecture.py)."""

from app.ai.client import (
    AIError,
    AIOutputInvalid,
    AIRefused,
    AIResult,
    AIUnavailable,
    ClaudeClient,
    RecordingNotFound,
)
from app.ai.schemas import Confidence, ExtractedField, is_confident
from app.ai.untrusted import BASE_SYSTEM_PROMPT, DocumentTooLarge, UntrustedDocument

__all__ = [
    "BASE_SYSTEM_PROMPT",
    "AIError",
    "AIOutputInvalid",
    "AIRefused",
    "AIResult",
    "AIUnavailable",
    "ClaudeClient",
    "Confidence",
    "DocumentTooLarge",
    "ExtractedField",
    "RecordingNotFound",
    "UntrustedDocument",
    "is_confident",
]

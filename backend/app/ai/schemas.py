"""Building blocks for the JSON structures the model fills in."""

from __future__ import annotations

from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")

# The model's own rating of how clearly the material states a value. Code treats anything other
# than "high" as unsure, which means yellow or a question to the officer, never green.
Confidence = Literal["high", "medium", "low"]


class ExtractedField(BaseModel, Generic[T]):
    """One value read from the material, with how sure the model is and the words it came from."""

    model_config = ConfigDict(extra="forbid")

    value: T | None
    confidence: Confidence
    evidence: str | None  # the words in the material the value was read from, if any


def is_confident(field: ExtractedField[T]) -> bool:
    """Only a 'high' rating with a value counts. Everything else must go to a human."""
    return field.value is not None and field.confidence == "high"

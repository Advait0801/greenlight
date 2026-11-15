"""Building blocks for the JSON structures the model fills in."""

from __future__ import annotations

import math
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
    """Only a 'high' rating with a usable value counts. Everything else must go to a human.
    A number that is not finite (NaN, infinity) is never usable."""
    if field.value is None or field.confidence != "high":
        return False
    if isinstance(field.value, float) and not math.isfinite(field.value):
        return False
    return True

"""Building blocks for the JSON structures the model fills in."""

from __future__ import annotations

import math
from typing import Any, Generic, Literal, TypeVar

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


class PersonalData:
    """Marks a field that holds details about a person (a traveller's name, a student ID, a phone number):
    `name: Annotated[ExtractedField[str], PERSONAL]`. Such fields are blanked before an answer is saved
    as a recording or written to the audit log (PROJECT_CONTEXT section 9: traveller details are not
    stored), so only the fact that something was read is kept."""

    def __repr__(self) -> str:
        return "PERSONAL"


PERSONAL = PersonalData()
NOT_STORED = "[personal details not stored]"


def _blank(value: Any) -> Any:
    if isinstance(value, ExtractedField):
        return value.model_copy(update={"value": None, "confidence": "low", "evidence": None})
    if isinstance(value, list):
        return []
    if isinstance(value, str):
        return NOT_STORED
    return None


def without_personal_data(model: BaseModel) -> BaseModel:
    """A copy of an answer with every field marked PERSONAL blanked, at any depth."""
    updates: dict[str, Any] = {}
    for name, info in type(model).model_fields.items():
        value = getattr(model, name)
        if any(isinstance(item, PersonalData) for item in info.metadata):
            updates[name] = _blank(value)
        elif isinstance(value, BaseModel):
            updates[name] = without_personal_data(value)
        elif isinstance(value, list) and any(isinstance(item, BaseModel) for item in value):
            updates[name] = [without_personal_data(item) if isinstance(item, BaseModel) else item for item in value]
    return model.model_copy(update=updates) if updates else model

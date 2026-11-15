"""Building blocks for the JSON structures the model fills in."""

from __future__ import annotations

import math
from typing import Annotated, Any, Generic, Literal, TypeVar, get_args, get_origin

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
    if isinstance(value, (list, tuple, dict)):
        return type(value)()
    if isinstance(value, str):
        return NOT_STORED if value else ""  # an empty field stays empty, so it never replays as present
    return None


def _marked(annotation: Any) -> bool:
    """True if PERSONAL appears anywhere in a type: on the field, inside Optional[...], list[...] or dict[...]."""
    if get_origin(annotation) is Annotated:
        if any(isinstance(item, PersonalData) for item in get_args(annotation)[1:]):
            return True
    return any(_marked(arg) for arg in get_args(annotation))


def _is_personal(info: Any) -> bool:
    return any(isinstance(item, PersonalData) for item in info.metadata) or _marked(info.annotation)


def holds_personal_data(model_type: type[BaseModel]) -> bool:
    """True if any field of the schema, at any depth, is marked PERSONAL."""
    seen: set[type[BaseModel]] = set()

    def walk(tp: Any) -> bool:
        if isinstance(tp, type) and issubclass(tp, BaseModel):
            if tp in seen:
                return False
            seen.add(tp)
            return any(_is_personal(info) or walk(info.annotation) for info in tp.model_fields.values())
        return any(walk(arg) for arg in get_args(tp))

    return walk(model_type)


def check_personal_schema(model_type: type[BaseModel]) -> None:
    """A PERSONAL field must be something that can be blanked and still replay: text, an ExtractedField,
    a list, a dict, a tuple, or optional. A required date of birth, say, would make a recording that can
    never be replayed, so such a schema is refused before any call is made."""
    for name, info in model_type.model_fields.items():
        if _is_personal(info):
            annotation = info.annotation
            base = get_origin(annotation) or annotation
            optional = type(None) in get_args(annotation)
            blankable = optional or base in (str, list, tuple, dict) or (
                isinstance(base, type) and issubclass(base, ExtractedField)
            )
            if not blankable:
                raise TypeError(f"{model_type.__name__}.{name} is PERSONAL but cannot be blanked; make it text or optional")
        else:
            for arg in (info.annotation, *get_args(info.annotation)):
                if isinstance(arg, type) and issubclass(arg, BaseModel) and arg is not model_type:
                    check_personal_schema(arg)


def _strip_evidence(value: Any) -> Any:
    if isinstance(value, ExtractedField):
        return value.model_copy(update={"evidence": None})
    if isinstance(value, BaseModel):
        return value.model_copy(update={name: _strip_evidence(getattr(value, name)) for name in type(value).model_fields})
    if isinstance(value, (list, tuple)):
        return type(value)(_strip_evidence(item) for item in value)
    if isinstance(value, dict):
        return {key: _strip_evidence(item) for key, item in value.items()}
    return value


def _redact(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return without_personal_data(value)
    if isinstance(value, (list, tuple)):
        return type(value)(_redact(item) for item in value)
    if isinstance(value, dict):
        return {key: _redact(item) for key, item in value.items()}
    return value


def without_personal_data(model: BaseModel) -> BaseModel:
    """A copy of an answer with every field marked PERSONAL blanked, at any depth (inside lists, tuples,
    dicts and optional fields). If the schema holds personal data anywhere, every `evidence` quote is
    dropped too, because a quote read for another field can contain a name."""
    updates: dict[str, Any] = {}
    for name, info in type(model).model_fields.items():
        value = getattr(model, name)
        updates[name] = _blank(value) if _is_personal(info) else _redact(value)
    copy = model.model_copy(update=updates)
    return _strip_evidence(copy) if holds_personal_data(type(model)) else copy

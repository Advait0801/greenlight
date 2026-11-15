"""The one place the app talks to Claude.

The model reads and drafts; it never decides. Every call:
  - sends trusted instructions in the system prompt and untrusted material wrapped as data,
  - asks for a JSON structure (structured output) described by a Pydantic model,
  - validates the answer against that model in code, the same way for live and recorded answers,
  - fails with a clear AIError instead of returning anything unvalidated.

AI_MODE selects live calls, replay of saved responses (`recorded`, used by every test), or live
calls that also save each response (`record`). Recorded mode never touches the network.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ValidationError

from app.ai.schemas import without_personal_data
from app.ai.untrusted import BASE_SYSTEM_PROMPT, UntrustedDocument, build_user_content
from app.config import AIMode, Settings, get_settings
from app.jsonutil import StrictJSONError, loads_strict

OutputT = TypeVar("OutputT", bound=BaseModel)
ModelRole = Literal["extract", "classify"]
TASK_NAME = re.compile(r"^[a-z0-9][a-z0-9_-]{1,60}$")
RECORDING_FORMAT = 1


class AIError(Exception):
    """Base class. Callers turn any AIError into a yellow 'could not read this' result, never green."""


class AIUnavailable(AIError):
    """The API cannot be called (no key, network, rate limit, outage)."""


class RecordingNotFound(AIError):
    """Recorded mode has no saved response for this exact request."""


class AIRefused(AIError):
    """The model declined the request."""


class AIOutputInvalid(AIError):
    """The answer did not match the requested structure (or was cut off)."""


@dataclass(frozen=True)
class AIResult(Generic[OutputT]):
    output: OutputT
    task: str
    model: str
    mode: AIMode
    request_key: str
    raw_text: str
    stop_reason: str | None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def audit_payload(self) -> dict[str, Any]:
        """What goes in the audit log: the model's output with personal fields blanked. Other fields keep
        their `evidence`, which quotes the document, so the log is private to the club."""
        return {
            "task": self.task,
            "model": self.model,
            "mode": self.mode.value,
            "request_key": self.request_key,
            "stop_reason": self.stop_reason,
            "output": without_personal_data(self.output).model_dump(mode="json") if isinstance(self.output, BaseModel) else json.loads(self.raw_text),
        }


@dataclass(frozen=True)
class PreparedRequest:
    task: str
    model_role: ModelRole
    model: str
    system: str
    user_content: list[dict[str, Any]]
    output_type: type[BaseModel]
    key: str
    summary: dict[str, Any]


class ClaudeClient:
    def __init__(self, settings: Settings | None = None, *, sdk_client: Any | None = None) -> None:
        self.settings = settings or get_settings()
        self._sdk_client = sdk_client

    # ----------------------------------------------------------------------------------------
    # Public API

    def extract(
        self,
        *,
        task: str,
        instructions: str,
        request: str,
        documents: list[UntrustedDocument],
        output_type: type[OutputT],
        model_role: ModelRole = "extract",
        max_tokens: int = 16000,
    ) -> AIResult[OutputT]:
        """Ask the model to read `documents` and fill in `output_type`.

        `instructions` (system prompt addition) and `request` (user-turn request) must be written
        by our code, never built from user input. User input goes in `documents`.
        """
        prepared = self.prepare(
            task=task,
            instructions=instructions,
            request=request,
            documents=documents,
            output_type=output_type,
            model_role=model_role,
        )
        mode = self.settings.ai_mode
        if mode is AIMode.RECORDED:
            raw_text, stop_reason, model = self._replay(prepared)
        else:
            raw_text, stop_reason, model = self._call_live(prepared, max_tokens)

        output = self._validate(prepared, raw_text, stop_reason)
        if mode is AIMode.RECORD:
            # Personal fields are blanked in the saved copy; a replay shows them as not read.
            self.save_recording(prepared, without_personal_data(output).model_dump_json(), stop_reason=stop_reason, model=model)
        return AIResult(
            output=output,
            task=task,
            model=model,
            mode=mode,
            request_key=prepared.key,
            raw_text=raw_text,
            stop_reason=stop_reason,
        )

    def prepare(
        self,
        *,
        task: str,
        instructions: str,
        request: str,
        documents: list[UntrustedDocument],
        output_type: type[BaseModel],
        model_role: ModelRole = "extract",
    ) -> PreparedRequest:
        if not TASK_NAME.match(task):
            raise ValueError(f"task name '{task}' must be lowercase letters, digits, '-' or '_'")
        system = f"{BASE_SYSTEM_PROMPT}\nTask: {task}\n{instructions.strip()}\n"
        user_content = build_user_content(request.strip(), documents)
        model = self.settings.model_extract if model_role == "extract" else self.settings.model_classify
        summary = {
            "task": task,
            "model_role": model_role,
            "system": system,
            "request": request.strip(),
            "documents": [
                {"name": doc.name, "media_type": doc.media_type, "fingerprint": doc.fingerprint} for doc in documents
            ],
            "output_type": output_type.__name__,
            "output_schema": output_type.model_json_schema(),
        }
        # The key covers everything that could change the answer except the model name, so a
        # model upgrade does not orphan the recordings (re-record deliberately when needed).
        key = hashlib.sha256(json.dumps(summary, sort_keys=True).encode("utf-8")).hexdigest()
        return PreparedRequest(
            task=task,
            model_role=model_role,
            model=model,
            system=system,
            user_content=user_content,
            output_type=output_type,
            key=key,
            summary=summary,
        )

    def recording_path(self, prepared: PreparedRequest) -> Path:
        return self.settings.ai_recordings_dir / prepared.task / f"{prepared.key}.json"

    def save_recording(
        self, prepared: PreparedRequest, raw_text: str, *, stop_reason: str | None = "end_turn", model: str | None = None
    ) -> Path:
        """Save a response for replay. The request is stored as fingerprints of the documents, not the
        documents; the response can still quote them in `evidence` (personal fields are blanked by the
        caller). Recordings are git-ignored; commit only ones made from the synthetic demo and test data."""
        path = self.recording_path(prepared)
        path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "format": RECORDING_FORMAT,
            "task": prepared.task,
            "key": prepared.key,
            "model": model or prepared.model,
            "model_role": prepared.model_role,
            "recorded_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
            "stop_reason": stop_reason,
            "request": {
                "request": prepared.summary["request"],
                "documents": prepared.summary["documents"],
                "output_type": prepared.summary["output_type"],
            },
            "response_text": raw_text,
        }
        path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return path

    # ----------------------------------------------------------------------------------------
    # Internals

    def _replay(self, prepared: PreparedRequest) -> tuple[str, str | None, str]:
        path = self.recording_path(prepared)
        if not path.is_file():
            raise RecordingNotFound(
                f"No recorded response for task '{prepared.task}' (key {prepared.key[:16]}…) in "
                f"{path.parent}. AI_MODE=recorded never calls the API. To create one, set "
                "ANTHROPIC_API_KEY and run the same request once with AI_MODE=record."
            )
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AIOutputInvalid(f"Recording {path.name} is not readable JSON: {exc}") from exc
        if not isinstance(record, dict) or record.get("format") != RECORDING_FORMAT:
            raise AIOutputInvalid(f"Recording {path.name} has an unknown format")
        if record.get("key") != prepared.key or record.get("task") != prepared.task:
            raise AIOutputInvalid(f"Recording {path.name} does not belong to this request")
        raw_text = record.get("response_text")
        if not isinstance(raw_text, str):
            raise AIOutputInvalid(f"Recording {path.name} has no response_text")
        stop_reason = record.get("stop_reason")
        model = record.get("model")
        return raw_text, stop_reason if isinstance(stop_reason, str) else None, model if isinstance(model, str) else prepared.model

    def _sdk(self) -> Any:
        if self._sdk_client is not None:
            return self._sdk_client
        key = self.settings.anthropic_api_key.get_secret_value() if self.settings.anthropic_api_key else ""
        if not key:
            raise AIUnavailable(
                "ANTHROPIC_API_KEY is not set, so the Claude API cannot be called. "
                "Set it in .env, or use AI_MODE=recorded to replay saved responses."
            )
        import anthropic

        self._sdk_client = anthropic.Anthropic(api_key=key, timeout=self.settings.ai_timeout_seconds, max_retries=2)
        return self._sdk_client

    def _call_live(self, prepared: PreparedRequest, max_tokens: int) -> tuple[str, str | None, str]:
        import anthropic

        sdk = self._sdk()
        try:
            response = sdk.messages.parse(
                model=prepared.model,
                max_tokens=max_tokens,
                system=prepared.system,
                messages=[{"role": "user", "content": prepared.user_content}],
                output_format=prepared.output_type,
            )
        except anthropic.AuthenticationError as exc:
            raise AIUnavailable("The Claude API rejected the API key.") from exc
        except anthropic.RateLimitError as exc:
            raise AIUnavailable("The Claude API is rate limiting requests; try again shortly.") from exc
        except anthropic.APITimeoutError as exc:
            raise AIUnavailable("The Claude API did not answer in time.") from exc
        except anthropic.APIConnectionError as exc:
            raise AIUnavailable("Could not reach the Claude API.") from exc
        except anthropic.BadRequestError as exc:
            raise AIUnavailable(f"The Claude API rejected the request: {exc.message}") from exc
        except anthropic.APIStatusError as exc:
            raise AIUnavailable(f"The Claude API returned an error ({exc.status_code}).") from exc
        except ValidationError as exc:
            # The SDK validates parsed output too; report it the same way as our own check.
            raise AIOutputInvalid(f"The answer did not match {prepared.output_type.__name__}: {exc}") from exc

        stop_reason = getattr(response, "stop_reason", None)
        if stop_reason == "refusal":
            raise AIRefused("The model declined to read this material.")
        raw_text = next(
            (block.text for block in getattr(response, "content", []) if getattr(block, "type", None) == "text"),
            None,
        )
        if raw_text is None:
            raise AIOutputInvalid("The answer contained no text block.")
        return raw_text, stop_reason, getattr(response, "model", prepared.model)

    def _validate(self, prepared: PreparedRequest, raw_text: str, stop_reason: str | None) -> Any:
        if stop_reason == "refusal":
            raise AIRefused("The model declined to read this material.")
        if stop_reason == "max_tokens":
            raise AIOutputInvalid("The answer was cut off before it was complete.")
        # Strict on two levels: the JSON itself (no duplicate keys, no NaN or Infinity) and the
        # types (no booleans read as numbers, no numbers read as text).
        try:
            loads_strict(raw_text)
        except (json.JSONDecodeError, StrictJSONError) as exc:
            raise AIOutputInvalid(f"The answer is not strict JSON: {exc}") from exc
        try:
            return prepared.output_type.model_validate_json(raw_text, strict=True)
        except ValidationError as exc:
            raise AIOutputInvalid(
                f"The answer did not match {prepared.output_type.__name__}: {exc.error_count()} problem(s)"
            ) from exc

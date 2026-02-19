"""
Provider-agnostic LLM backend interface for what-do-i-become.

OpenAI is implemented now.
Anthropic and Grok are planned and intentionally scaffolded.
"""

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class LLMEvent:
    type: str
    text: str = ""
    name: str = ""
    call_id: str = ""
    arguments: Optional[Dict[str, Any]] = None


@dataclass
class LLMTurnResult:
    events: List[LLMEvent]
    output_text: str = ""


class LLMBackend(ABC):
    provider: str
    model: str

    @abstractmethod
    def create_context(self, wake_message: str) -> Any:
        pass

    @abstractmethod
    def add_user_message(self, context: Any, message: str) -> None:
        pass

    @abstractmethod
    def run_turn(self, context: Any, instructions: str, tools: List[Dict[str, Any]]) -> LLMTurnResult:
        pass

    @abstractmethod
    def add_tool_result(self, context: Any, call_id: str, output_json: str) -> None:
        pass

    @abstractmethod
    def generate_text(self, instructions: str, user_prompt: str) -> str:
        pass


def _extract_text_from_item(item: Any) -> str:
    if hasattr(item, "content") and item.content:
        texts = []
        for part in item.content:
            text = getattr(part, "text", None)
            if text:
                texts.append(text)
        if texts:
            return "\n".join(texts)
    text = getattr(item, "text", None)
    return text or ""


class OpenAIResponsesBackend(LLMBackend):
    def __init__(self, model: str):
        from openai import OpenAI  # lazy import so other providers can be added cleanly

        self.provider = "openai"
        self.model = model
        self._client = OpenAI()

    def create_context(self, wake_message: str) -> List[Any]:
        return [{"role": "user", "content": wake_message}]

    def add_user_message(self, context: List[Any], message: str) -> None:
        context.append({"role": "user", "content": message})

    def run_turn(
        self, context: List[Any], instructions: str, tools: List[Dict[str, Any]]
    ) -> LLMTurnResult:
        response = self._client.responses.create(
            model=self.model,
            instructions=instructions,
            tools=tools,
            input=context,
        )

        # Keep provider-native outputs in context for best turn-to-turn fidelity.
        context.extend(response.output)

        events: List[LLMEvent] = []
        for item in response.output:
            item_type = getattr(item, "type", None)
            if item_type == "function_call":
                raw_args = getattr(item, "arguments", None)
                try:
                    arguments = json.loads(raw_args) if raw_args else {}
                except (TypeError, json.JSONDecodeError):
                    arguments = {"_raw": str(raw_args)}
                events.append(
                    LLMEvent(
                        type="function_call",
                        name=getattr(item, "name", ""),
                        call_id=getattr(item, "call_id", ""),
                        arguments=arguments,
                    )
                )
            else:
                text = _extract_text_from_item(item)
                if text:
                    events.append(LLMEvent(type="text", text=text))

        return LLMTurnResult(events=events, output_text=getattr(response, "output_text", "") or "")

    def add_tool_result(self, context: List[Any], call_id: str, output_json: str) -> None:
        context.append(
            {
                "type": "function_call_output",
                "call_id": call_id,
                "output": output_json,
            }
        )

    def generate_text(self, instructions: str, user_prompt: str) -> str:
        response = self._client.responses.create(
            model=self.model,
            instructions=instructions,
            input=[{"role": "user", "content": user_prompt}],
        )
        return getattr(response, "output_text", "") or ""


def _resolve_model_name() -> str:
    return (
        os.environ.get("WDIB_LLM_MODEL")
        or os.environ.get("WDIB_MODEL")
        or os.environ.get("PI_AGENT_MODEL")
        or "gpt-5"
    )


def create_llm_backend() -> LLMBackend:
    provider = (os.environ.get("WDIB_LLM_PROVIDER", "openai") or "openai").strip().lower()
    model = _resolve_model_name()

    if provider == "openai":
        return OpenAIResponsesBackend(model=model)

    if provider in {"anthropic", "grok", "xai", "gemini", "google"}:
        raise RuntimeError(
            f"LLM provider '{provider}' is configured but not implemented yet. "
            "The backend interface is ready for it; for now set WDIB_LLM_PROVIDER=openai."
        )

    raise RuntimeError(
        f"Unsupported WDIB_LLM_PROVIDER='{provider}'. "
        "Expected one of: openai, anthropic, grok, gemini."
    )

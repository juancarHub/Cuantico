"""Proveedor LLM configurable para Cuántico.

Este módulo separa el bucle principal del SDK concreto usado por el modelo.
Por defecto conserva Gemini, pero permite seleccionar OpenAI desde .env.
"""
from __future__ import annotations

import json
import inspect
from dataclasses import dataclass
from typing import Any, Callable

import config


@dataclass
class ChatResult:
    text: str


class BaseChat:
    def send_message(self, text: str) -> ChatResult:
        raise NotImplementedError


class BaseLLMProvider:
    name = "base"

    def create_chat(self, system_prompt: str, tools: list[Callable[..., Any]]) -> BaseChat:
        raise NotImplementedError


def _build_tool_schema(fn: Callable[..., Any]) -> dict[str, Any]:
    """Convierte una función Python sencilla a esquema tools de OpenAI."""
    sig = inspect.signature(fn)
    properties: dict[str, Any] = {}
    required: list[str] = []

    for name, param in sig.parameters.items():
        annotation = param.annotation
        json_type = "string"
        if annotation in (int, "int"):
            json_type = "integer"
        elif annotation in (float, "float"):
            json_type = "number"
        elif annotation in (bool, "bool"):
            json_type = "boolean"

        properties[name] = {"type": json_type}
        if param.default is inspect._empty:
            required.append(name)

    return {
        "type": "function",
        "function": {
            "name": fn.__name__,
            "description": inspect.getdoc(fn) or "",
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": False,
            },
        },
    }


class GeminiChat(BaseChat):
    def __init__(self, client: Any, model: str, system_prompt: str, tools: list[Callable[..., Any]]):
        from google.genai import types

        grounding = types.Tool(google_search=types.GoogleSearch())
        tool_cfg = types.ToolConfig(include_server_side_tool_invocations=True)
        cfg = types.GenerateContentConfig(
            system_instruction=system_prompt,
            tools=[*tools, grounding],
            tool_config=tool_cfg,
        )
        self._chat = client.chats.create(model=model, config=cfg)

    def send_message(self, text: str) -> ChatResult:
        response = self._chat.send_message(text)
        return ChatResult(text=(response.text or "").strip())


class GeminiProvider(BaseLLMProvider):
    name = "gemini"

    def __init__(self) -> None:
        from google import genai

        self._client = genai.Client(api_key=config.GEMINI_API_KEY)
        self._model = config.GEMINI_MODEL

    def create_chat(self, system_prompt: str, tools: list[Callable[..., Any]]) -> BaseChat:
        return GeminiChat(self._client, self._model, system_prompt, tools)


class OpenAIChat(BaseChat):
    def __init__(self, client: Any, model: str, system_prompt: str, tools: list[Callable[..., Any]]):
        self._client = client
        self._model = model
        self._tools_by_name = {fn.__name__: fn for fn in tools}
        self._tools = [_build_tool_schema(fn) for fn in tools]
        self._messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]

    def send_message(self, text: str) -> ChatResult:
        self._messages.append({"role": "user", "content": text})

        for _ in range(8):
            response = self._client.chat.completions.create(
                model=self._model,
                messages=self._messages,
                tools=self._tools,
                tool_choice="auto",
            )
            msg = response.choices[0].message
            self._messages.append(msg.model_dump(exclude_none=True))

            tool_calls = msg.tool_calls or []
            if not tool_calls:
                return ChatResult(text=(msg.content or "").strip())

            for call in tool_calls:
                fn = self._tools_by_name.get(call.function.name)
                if not fn:
                    result = f"fallo: tool desconocida {call.function.name}"
                else:
                    try:
                        args = json.loads(call.function.arguments or "{}")
                        result = str(fn(**args))
                    except Exception as exc:
                        result = f"fallo: {exc}"

                self._messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": result,
                    }
                )

        return ChatResult(text="Se me ha hecho bola el festival de tools. Repite eso más corto, Fran.")


class OpenAIProvider(BaseLLMProvider):
    name = "openai"

    def __init__(self) -> None:
        from openai import OpenAI

        self._client = OpenAI(api_key=config.OPENAI_API_KEY)
        self._model = config.OPENAI_MODEL

    def create_chat(self, system_prompt: str, tools: list[Callable[..., Any]]) -> BaseChat:
        return OpenAIChat(self._client, self._model, system_prompt, tools)


def create_provider() -> BaseLLMProvider:
    provider = config.LLM_PROVIDER.lower()
    if provider == "openai":
        return OpenAIProvider()
    if provider == "gemini":
        return GeminiProvider()
    raise RuntimeError(f"LLM_PROVIDER no soportado: {config.LLM_PROVIDER}")

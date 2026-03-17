"""Claude API client with function-calling for Munshi tools."""

from __future__ import annotations

import json
from typing import Any

from anthropic import AsyncAnthropic
from anthropic.types import Message, ToolUseBlock
from loguru import logger

from munshi.ai.prompt_templates import MUNSHI_SYSTEM_PROMPT
from munshi.ai.tool_definitions import MUNSHI_TOOLS
from munshi.config import settings


class ToolCall:
    """Represents a tool call extracted from Claude's response."""

    def __init__(self, name: str, inputs: dict[str, Any], tool_use_id: str) -> None:
        self.name = name
        self.inputs = inputs
        self.tool_use_id = tool_use_id

    def __repr__(self) -> str:
        return f"ToolCall({self.name}, {self.inputs})"


class ClaudeClient:
    """
    Wraps the Anthropic API with:
    - Munshi system prompt
    - Tool/function-calling for all shop operations
    - Short conversation context (last N turns)
    """

    MAX_CONTEXT_TURNS = 10  # Keep last 10 turns to limit token usage

    def __init__(self) -> None:
        if not settings.anthropic_api_key:
            logger.warning("ANTHROPIC_API_KEY not set — Claude AI features will be disabled.")
            self._client = None
        else:
            self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._conversation: list[dict] = []

    def _trim_context(self) -> None:
        if len(self._conversation) > self.MAX_CONTEXT_TURNS * 2:
            # Keep system context intact, trim oldest turns
            self._conversation = self._conversation[-(self.MAX_CONTEXT_TURNS * 2):]

    async def process(self, user_text: str) -> tuple[str | None, list[ToolCall]]:
        """
        Send user text to Claude and get back:
        - text_response: spoken response (may be None if tool use is needed)
        - tool_calls: list of tool calls to execute

        Returns ("", []) on failure or if API unavailable.
        """
        if not self._client:
            return None, []

        self._conversation.append({"role": "user", "content": user_text})
        self._trim_context()

        try:
            response: Message = await self._client.messages.create(
                model=settings.claude_model,
                max_tokens=256,
                system=MUNSHI_SYSTEM_PROMPT,
                tools=MUNSHI_TOOLS,
                messages=self._conversation,
            )
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            return None, []

        # Parse response
        text_parts = []
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(
                    name=block.name,
                    inputs=block.input,
                    tool_use_id=block.id,
                ))

        text_response = " ".join(text_parts).strip() or None

        # Add assistant turn to context
        self._conversation.append({"role": "assistant", "content": response.content})

        logger.debug(f"Claude → text='{text_response}' tools={[t.name for t in tool_calls]}")
        return text_response, tool_calls

    async def send_tool_results(self, tool_results: list[dict]) -> str:
        """
        Send tool execution results back to Claude and get the final spoken response.
        tool_results: [{"tool_use_id": ..., "content": ...}, ...]
        """
        if not self._client:
            return ""

        self._conversation.append({
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": r["tool_use_id"], "content": r["content"]}
                for r in tool_results
            ],
        })

        try:
            response: Message = await self._client.messages.create(
                model=settings.claude_model,
                max_tokens=150,
                system=MUNSHI_SYSTEM_PROMPT,
                tools=MUNSHI_TOOLS,
                messages=self._conversation,
            )
        except Exception as e:
            logger.error(f"Claude API error (tool results): {e}")
            return ""

        self._conversation.append({"role": "assistant", "content": response.content})

        text_parts = [b.text for b in response.content if b.type == "text"]
        return " ".join(text_parts).strip()

    def reset_context(self) -> None:
        """Clear conversation history (e.g. at start of new session)."""
        self._conversation.clear()

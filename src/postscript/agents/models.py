"""Model providers. Bedrock for the real thing; the scripted clerk for offline runs and tests.

The scripted clerk implements the Strands Model interface, so the whole agent loop (tools, MCP,
hooks, interventions, Cedar) runs exactly as it would with Claude, minus the model call.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncGenerator, AsyncIterable
from typing import Any

from strands.models import Model
from strands.types.content import Messages
from strands.types.streaming import StreamEvent
from strands.types.tools import ToolSpec

from ..config import settings


def make_model(role: str = "runner") -> Model:
    """Pick the model provider from settings. role is 'runner' or 'intake'."""
    if settings.model == "bedrock":
        from strands.models import BedrockModel

        kwargs: dict[str, Any] = {"region_name": settings.region, "temperature": 0.1}
        if settings.model_id:
            kwargs["model_id"] = settings.model_id
        return BedrockModel(**kwargs)
    from .clerk import ClerkBrain

    return ScriptedModel(ClerkBrain(role))


class ScriptedModel(Model):
    """A deterministic 'model' that plays a careful estate clerk. No network, no tokens."""

    def __init__(self, brain: Any):
        self.brain = brain
        self._config: dict[str, Any] = {"model_id": "postscript-scripted-clerk"}

    def update_config(self, **model_config: Any) -> None:
        self._config.update(model_config)

    def get_config(self) -> dict[str, Any]:
        return self._config

    async def structured_output(self, output_model, prompt: Messages, system_prompt: str | None = None,
                                **kwargs: Any) -> AsyncGenerator[dict[str, Any], None]:
        yield {"output": self.brain.structured(output_model, prompt, system_prompt)}

    async def stream(self, messages: Messages, tool_specs: list[ToolSpec] | None = None,
                     system_prompt: str | None = None, **kwargs: Any) -> AsyncIterable[StreamEvent]:
        step = self.brain.next(messages, tool_specs or [], system_prompt)
        yield {"messageStart": {"role": "assistant"}}
        if step[0] == "tool":
            _, name, args = step
            tool_use_id = f"tooluse_{uuid.uuid4().hex[:12]}"
            yield {"contentBlockStart": {"start": {"toolUse": {"name": name, "toolUseId": tool_use_id}}}}
            yield {"contentBlockDelta": {"delta": {"toolUse": {"input": json.dumps(args)}}}}
            yield {"contentBlockStop": {}}
            yield {"messageStop": {"stopReason": "tool_use"}}
        else:
            yield {"contentBlockStart": {"start": {}}}
            yield {"contentBlockDelta": {"delta": {"text": step[1]}}}
            yield {"contentBlockStop": {}}
            yield {"messageStop": {"stopReason": "end_turn"}}
        yield {"metadata": {"usage": {"inputTokens": 0, "outputTokens": 0, "totalTokens": 0},
                            "metrics": {"latencyMs": 0}}}

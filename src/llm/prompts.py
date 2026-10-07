"""Build Ollama-compatible messages for selecting the next agent action."""

import json
from typing import Any, Sequence

from src.agent.contracts import Goal, Observation
from src.llm.schema import TOOL_NAMES


_TOOL_DESCRIPTIONS = {
    "get_product": "Look up a full product record; requires product_id.",
    "get_product_price": "Look up a product's price; requires product_id.",
    "check_inventory": "Look up a product's stock; requires product_id.",
    "finish": "Stop the agent loop; requires no arguments and needs evidence in observations.",
}

_SYSTEM_MESSAGE = """You select the next action for a single-agent product assistant.
Choose exactly one available tool based on the goal and the evidence so far.
Never claim that a tool has run; the application will execute the selected action.
Choose finish only when the observations provide evidence that the goal is complete.
Return only the action object required by the supplied JSON schema, with no prose."""


def build_decision_messages(
    goal: Goal,
    observations: Sequence[Observation],
    products: Sequence[dict[str, Any]] = (),
) -> list[dict[str, str]]:
    """Build the system and user messages for one model decision."""
    tool_descriptions = [
        {"name": name, "description": _TOOL_DESCRIPTIONS[name]}
        for name in TOOL_NAMES
    ]
    observation_payload = [
        {"source": observation.source, "result": observation.result}
        for observation in observations
    ]

    user_context = {
        "goal": goal.text,
        "available_tools": tool_descriptions,
        "product_catalog": list(products),
        "observations": observation_payload,
        "response_shape": {
            "tool_name": "one available tool name",
            "arguments": "arguments required by that tool",
        },
    }

    return [
        {"role": "system", "content": _SYSTEM_MESSAGE},
        {
            "role": "user",
            "content": json.dumps(user_context, ensure_ascii=False, default=str),
        },
    ]

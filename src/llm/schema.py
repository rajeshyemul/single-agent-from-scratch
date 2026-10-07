"""JSON Schema for a single proposed agent action."""

from typing import Any


TOOL_NAMES = (
    "get_product",
    "get_product_price",
    "check_inventory",
    "finish",
)

_TOOL_ARGUMENTS: dict[str, dict[str, Any]] = {
    "get_product": {
        "type": "object",
        "properties": {"product_id": {"type": "string"}},
        "required": ["product_id"],
        "additionalProperties": False,
    },
    "get_product_price": {
        "type": "object",
        "properties": {"product_id": {"type": "string"}},
        "required": ["product_id"],
        "additionalProperties": False,
    },
    "check_inventory": {
        "type": "object",
        "properties": {"product_id": {"type": "string"}},
        "required": ["product_id"],
        "additionalProperties": False,
    },
    "finish": {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    },
}


def _action_variant(tool_name: str) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "tool_name": {"type": "string", "enum": [tool_name]},
            "arguments": _TOOL_ARGUMENTS[tool_name],
        },
        "required": ["tool_name", "arguments"],
        "additionalProperties": False,
    }


# Pass this schema as Ollama's `format` value for constrained JSON output.
ACTION_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "oneOf": [_action_variant(tool_name) for tool_name in TOOL_NAMES],
}

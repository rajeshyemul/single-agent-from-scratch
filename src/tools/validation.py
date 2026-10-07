from typing import Any

from src.agent.contracts import Action


VALID_TOOLS = {
    "get_product",
    "get_product_price",
    "check_inventory",
    "finish",
}

TOOL_ARGUMENTS: dict[str, dict[str, type]] = {
    "get_product": {"product_id": str},
    "get_product_price": {"product_id": str},
    "check_inventory": {"product_id": str},
    "finish": {},
}


def validate_action(action: Any) -> bool:
    """
    Validate a proposed action before execution.
    This prevents malformed or unknown tool calls.
    """
    if not isinstance(action, Action):
        return False

    if not isinstance(action.tool_name, str):
        return False

    if action.tool_name not in VALID_TOOLS:
        return False

    if not isinstance(action.arguments, dict):
        return False

    expected_arguments = TOOL_ARGUMENTS[action.tool_name]
    if action.arguments.keys() != expected_arguments.keys():
        return False

    for argument_name, expected_type in expected_arguments.items():
        value = action.arguments[argument_name]
        if not isinstance(value, expected_type):
            return False
        if isinstance(value, str) and not value.strip():
            return False

    return True
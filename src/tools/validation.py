from typing import Any


VALID_TOOLS = {
    "get_product",
    "get_product_price",
    "check_inventory",
    "finish",
}


def validate_action(action: Any) -> bool:
    """
    Validate a proposed action before execution.
    This prevents malformed or unknown tool calls.
    """
    if action is None:
        return False

    if not hasattr(action, "tool_name"):
        return False

    if not hasattr(action, "arguments"):
        return False

    if action.tool_name not in VALID_TOOLS:
        return False

    if not isinstance(action.arguments, dict):
        return False

    required_args = {
        "get_product": {"product_id"},
        "get_product_price": {"product_id"},
        "check_inventory": {"product_id"},
        "finish": set(),
    }

    expected = required_args.get(action.tool_name, set())
    if not expected.issubset(action.arguments.keys()):
        return False

    return True
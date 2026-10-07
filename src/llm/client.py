import json
import os
from typing import Any, List

import ollama

from src.agent.contracts import Action, FinalAnswer, Goal, Observation
from src.llm.prompts import build_decision_messages
from src.llm.schema import ACTION_RESPONSE_SCHEMA
from src.tools.product_tools import get_all_products
from src.tools.validation import validate_action


def _combined_product_facts(observations: List[Observation]) -> List[dict[str, Any]]:
    facts_by_product: dict[str, dict[str, Any]] = {}
    for observation in observations:
        result = observation.result
        if not isinstance(result, dict):
            continue

        product_id = result.get("product_id")
        if product_id is None:
            continue

        facts_by_product.setdefault(product_id, {}).update(result)

    return list(facts_by_product.values())


class LLMClient:
    """
    Local Ollama-backed decision client for a single-agent loop.
    """

    def __init__(
        self,
        model: str | None = None,
        host: str | None = None,
        client: Any | None = None,
    ):
        self.model = model or os.getenv("OLLAMA_MODEL", "llama3.2:latest")
        ollama_host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.client = client if client is not None else ollama.Client(host=ollama_host)

    def decide_next_action(self, goal: Goal, observations: List[Observation]) -> Action:
        messages = build_decision_messages(
            goal,
            observations,
            products=get_all_products(),
        )

        try:
            response = self.client.chat(
                model=self.model,
                messages=messages,
                format=ACTION_RESPONSE_SCHEMA,
                options={"temperature": 0},
                stream=False,
            )
        except Exception as exc:
            raise RuntimeError(
                f"Ollama request failed for model {self.model!r}. "
                "Check that Ollama is running and the model is available."
            ) from exc

        content = response.message.content
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Ollama returned an empty or invalid action response.")

        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError("Ollama returned malformed JSON for the action.") from exc

        if (
            not isinstance(payload, dict)
            or set(payload) != {"tool_name", "arguments"}
            or not isinstance(payload["tool_name"], str)
            or not isinstance(payload["arguments"], dict)
        ):
            raise ValueError("Ollama returned an action with an invalid structure.")

        action = Action(
            tool_name=payload["tool_name"],
            arguments=payload["arguments"],
        )
        if not validate_action(action):
            raise ValueError("Ollama returned an action that failed validation.")

        return action

    def goal_is_complete(self, goal: Goal, observations: List[Observation]) -> bool:
        goal_text = goal.text.lower()
        requires_price = "under" in goal_text and "5000" in goal_text
        requires_stock = "stock" in goal_text

        if not requires_price and not requires_stock:
            return False

        for facts in _combined_product_facts(observations):
            price = facts.get("price")
            stock = facts.get("stock")
            price_satisfied = not requires_price or (
                isinstance(price, (int, float)) and price <= 5000
            )
            stock_satisfied = not requires_stock or (
                isinstance(stock, (int, float)) and stock > 0
            )
            if price_satisfied and stock_satisfied:
                return True

        return False

    def build_final_answer(self, goal: Goal, observations: List[Observation]) -> FinalAnswer:
        for facts in _combined_product_facts(observations):
            product_name = facts.get("name")
            price = facts.get("price")
            stock = facts.get("stock")

            if not product_name:
                continue

            details = []
            if price is not None:
                details.append(f"price ₹{price}")
            if stock is not None:
                details.append(f"stock {stock}")

            if details:
                return FinalAnswer(
                    text=(
                        f"I found {product_name} with {' and '.join(details)}. "
                        "This satisfies the goal."
                    )
                )

        return FinalAnswer(text="I could not complete the goal with the available observations.")
from typing import List

from src.agent.contracts import Action, FinalAnswer, Goal, Observation


class LLMClient:
    """
    Minimal decision policy for a single-agent loop.
    This is intentionally small and deterministic.
    """

    def __init__(self):
        pass

    def decide_next_action(self, goal: Goal, observations: List[Observation]) -> Action:
        goal_text = goal.text.lower()

        if not observations:
            if "running shoes" in goal_text or "running shoe" in goal_text:
                return Action(tool_name="get_product", arguments={"product_id": "P1001"})
            if "yoga mat" in goal_text:
                return Action(tool_name="get_product", arguments={"product_id": "P1002"})
            if "backpack" in goal_text:
                return Action(tool_name="get_product", arguments={"product_id": "P1003"})
            return Action(tool_name="get_product", arguments={"product_id": "P1001"})

        last_result = observations[-1].result

        if isinstance(last_result, dict) and "error" in last_result:
            return Action(tool_name="finish", arguments={})

        # If we already have the product record, decide next based on goal.
        if isinstance(last_result, dict) and "product_id" in last_result:
            if "under" in goal_text and "5000" in goal_text:
                if last_result.get("price", 0) <= 5000:
                    return Action(
                        tool_name="check_inventory",
                        arguments={"product_id": last_result["product_id"]},
                    )
                return Action(tool_name="finish", arguments={})

            if "stock" in goal_text or "in stock" in goal_text:
                return Action(
                    tool_name="check_inventory",
                    arguments={"product_id": last_result["product_id"]},
                )

        # If the last observation was stock info, decide whether the goal is satisfied.
        if isinstance(last_result, dict) and "stock" in last_result:
            if self.goal_is_complete(goal, observations):
                return Action(tool_name="finish", arguments={})
            return Action(tool_name="finish", arguments={})

        if self.goal_is_complete(goal, observations):
            return Action(tool_name="finish", arguments={})

        return Action(tool_name="finish", arguments={})

    def goal_is_complete(self, goal: Goal, observations: List[Observation]) -> bool:
        goal_text = goal.text.lower()

        if "under" in goal_text and "5000" in goal_text:
            for obs in observations:
                result = obs.result
                if not isinstance(result, dict):
                    continue

                price = result.get("price")
                stock = result.get("stock")
                product_name = result.get("name")

                if price is not None and stock is not None and product_name:
                    if price <= 5000 and stock > 0:
                        return True

        if "in stock" in goal_text:
            for obs in observations:
                result = obs.result
                if isinstance(result, dict):
                    stock = result.get("stock")
                    if stock is not None and stock > 0:
                        return True

        return False

    def build_final_answer(self, goal: Goal, observations: List[Observation]) -> FinalAnswer:
        goal_text = goal.text.lower()

        for obs in observations:
            result = obs.result
            if not isinstance(result, dict):
                continue

            price = result.get("price")
            stock = result.get("stock")
            product_name = result.get("name")

            if product_name and price is not None and stock is not None:
                if price <= 5000 and stock > 0:
                    return FinalAnswer(
                        text=(
                            f"I found {product_name} at ₹{price} with stock {stock}. "
                            "This satisfies the goal."
                        )
                    )

        return FinalAnswer(text="I could not complete the goal with the available observations.")
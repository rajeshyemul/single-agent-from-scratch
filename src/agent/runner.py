from src.agent.contracts import Action, Goal, Observation
from src.llm.client import LLMClient
from src.tools.product_tools import (
    check_inventory,
    get_product,
    get_product_price,
)
from src.tools.validation import validate_action


class AgentRunner:
    """
    Responsible for:
    1. goal
    2. action proposal
    3. validation
    4. tool execution
    5. observation capture
    6. final answer generation
    """

    def __init__(self, llm_client=None):
        self.llm_client = llm_client or LLMClient()

    def execute_action(self, action: Action):
        """
        Execution boundary:
        - validate action
        - map tool name to function
        - execute the real tool
        - return the result
        """
        if action.tool_name == "finish":
            return {
                "status": "success",
                "result": {"message": "Goal completed"},
            }

        if not validate_action(action):
            return {
                "status": "error",
                "message": "Invalid action or missing required arguments.",
            }

        tool_map = {
            "get_product": get_product,
            "get_product_price": get_product_price,
            "check_inventory": check_inventory,
        }

        tool_fn = tool_map.get(action.tool_name)

        if tool_fn is None:
            return {
                "status": "error",
                "message": f"Unknown tool: {action.tool_name}",
            }

        try:
            result = tool_fn(**action.arguments)
            return {
                "status": "success",
                "result": result,
            }
        except TypeError:
            return {
                "status": "error",
                "message": "Tool called with invalid arguments.",
            }
        except Exception as exc:
            return {
                "status": "error",
                "message": f"Tool execution failed: {str(exc)}",
            }

    def run(self, goal: Goal, max_iterations: int = 5):
        observations: list[Observation] = []

        for iteration in range(max_iterations):
            next_action = self.llm_client.decide_next_action(goal, observations)

            if next_action.tool_name == "finish":
                if self.llm_client.goal_is_complete(goal, observations):
                    final_answer = self.llm_client.build_final_answer(goal, observations)
                    return {
                        "status": "completed",
                        "final_answer": final_answer.text,
                        "observations": observations,
                    }

                return {
                    "status": "failed",
                    "final_answer": "The agent stopped because the goal could not be completed with the available evidence.",
                    "observations": observations,
                }

            execution = self.execute_action(next_action)

            if execution["status"] == "error":
                return {
                    "status": "failed",
                    "final_answer": f"Goal could not be completed: {execution['message']}",
                    "observations": observations,
                }

            new_observation = Observation(result=execution["result"], source="tool")
            observations.append(new_observation)

            # Prevent endless loops on repeated state.
            if len(observations) >= 2:
                last_two = [obs.result for obs in observations[-2:]]
                if last_two[0] == last_two[1]:
                    return {
                        "status": "failed",
                        "final_answer": "The agent detected repeated observations and stopped to avoid a loop.",
                        "observations": observations,
                    }

            if self.llm_client.goal_is_complete(goal, observations):
                final_answer = self.llm_client.build_final_answer(goal, observations)
                return {
                    "status": "completed",
                    "final_answer": final_answer.text,
                    "observations": observations,
                }

        return {
            "status": "max_iterations_reached",
            "final_answer": "The agent stopped because it hit the safety limit.",
            "observations": observations,
        }
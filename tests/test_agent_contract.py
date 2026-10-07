import json
from types import SimpleNamespace

import pytest

from src.agent.contracts import Action, Goal, Observation
from src.agent.runner import AgentRunner
from src.llm.client import LLMClient
from src.tools.validation import validate_action


class FakeOllamaClient:
    def __init__(self, content=None, error=None):
        self.content = content
        self.error = error
        self.last_request = None

    def chat(self, **kwargs):
        self.last_request = kwargs
        if self.error is not None:
            raise self.error
        return SimpleNamespace(message=SimpleNamespace(content=self.content))


class ScriptedLLMClient:
    def __init__(self, actions):
        self.actions = list(actions)
        self.evidence_client = LLMClient(client=FakeOllamaClient(content=""))

    def decide_next_action(self, goal, observations):
        return self.actions.pop(0)

    def goal_is_complete(self, goal, observations):
        return self.evidence_client.goal_is_complete(goal, observations)

    def build_final_answer(self, goal, observations):
        return self.evidence_client.build_final_answer(goal, observations)


def test_goal_and_action_contract():
    goal = Goal(text="Find a product under 5000 INR")
    action = Action(tool_name="get_product", arguments={"product_id": "P1001"})

    assert goal.text == "Find a product under 5000 INR"
    assert action.tool_name == "get_product"
    assert action.arguments["product_id"] == "P1001"


def test_observation_data_shape():
    observation = Observation(result={"product_id": "P1001", "price": 4999}, source="tool")

    assert observation.source == "tool"
    assert observation.result["product_id"] == "P1001"
    assert observation.result["price"] == 4999


def test_execute_action_success():
    runner = AgentRunner()
    action = Action(tool_name="get_product", arguments={"product_id": "P1001"})

    result = runner.execute_action(action)

    assert result["status"] == "success"
    product = result["result"]
    assert isinstance(product, dict)
    assert product["product_id"] == "P1001"
    assert product["name"] == "Running Shoes"


def test_execute_action_invalid_tool_rejected():
    runner = AgentRunner()
    action = Action(tool_name="unknown_tool", arguments={"product_id": "P1001"})

    result = runner.execute_action(action)

    assert result["status"] == "error"
    assert "Invalid action" in result["message"] or "Unknown tool" in result["message"]


def test_validate_action_requires_exact_argument_shape():
    assert validate_action(Action(tool_name="get_product", arguments={"product_id": "P1001"}))
    assert validate_action(Action(tool_name="finish", arguments={}))

    invalid_actions = [
        None,
        {"tool_name": "get_product", "arguments": {"product_id": "P1001"}},
        Action(tool_name="unknown_tool", arguments={}),
        Action(tool_name="get_product", arguments={}),
        Action(tool_name="get_product", arguments={"product_id": "P1001", "extra": True}),
        Action(tool_name="get_product", arguments={"product_id": 1001}),
        Action(tool_name="get_product", arguments={"product_id": "  "}),
        Action(tool_name="finish", arguments={"product_id": "P1001"}),
    ]

    assert all(not validate_action(action) for action in invalid_actions)


def test_llm_client_parses_valid_ollama_response():
    fake_ollama = FakeOllamaClient(
        content=json.dumps(
            {"tool_name": "get_product", "arguments": {"product_id": "P1001"}}
        )
    )
    client = LLMClient(model="test-model", client=fake_ollama)

    action = client.decide_next_action(Goal(text="Find running shoes"), [])

    assert action == Action(tool_name="get_product", arguments={"product_id": "P1001"})
    assert fake_ollama.last_request is not None
    assert fake_ollama.last_request["model"] == "test-model"
    assert fake_ollama.last_request["format"]["type"] == "object"


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        json.dumps({"tool_name": "unknown_tool", "arguments": {}}),
        json.dumps({"tool_name": "get_product", "arguments": {"product_id": 1001}}),
        json.dumps({"tool_name": "get_product", "arguments": {"product_id": "P1001", "extra": True}}),
    ],
)
def test_llm_client_rejects_malformed_ollama_response(content):
    client = LLMClient(client=FakeOllamaClient(content=content))

    with pytest.raises(ValueError):
        client.decide_next_action(Goal(text="Find running shoes"), [])


def test_agent_loop_handles_llm_failure():
    fake_ollama = FakeOllamaClient(error=ConnectionError("Ollama is unavailable"))
    runner = AgentRunner(llm_client=LLMClient(client=fake_ollama))

    result = runner.run(Goal(text="Find a product"))

    assert result["status"] == "failed"
    assert "decision failed" in result["final_answer"]
    assert result["observations"] == []


def test_agent_loop_rejects_invalid_llm_action():
    class InvalidActionLLMClient:
        def decide_next_action(self, goal, observations):
            return Action(tool_name="unknown_tool", arguments={})

    runner = AgentRunner(llm_client=InvalidActionLLMClient())

    result = runner.run(Goal(text="Find a product"))

    assert result["status"] == "failed"
    assert "invalid action" in result["final_answer"]
    assert result["observations"] == []


def test_agent_loop_completes_goal():
    runner = AgentRunner(
        llm_client=ScriptedLLMClient(
            [Action(tool_name="get_product", arguments={"product_id": "P1001"})]
        )
    )
    goal = Goal(text="Find a running shoe under 5000 INR in stock")

    result = runner.run(goal, max_iterations=5)

    assert result["status"] == "completed"
    assert "Running Shoes" in result["final_answer"]


def test_agent_loop_stops_on_max_iterations():
    runner = AgentRunner(
        llm_client=ScriptedLLMClient(
            [Action(tool_name="get_product", arguments={"product_id": "P1001"})]
        )
    )
    goal = Goal(text="Describe a product")

    result = runner.run(goal, max_iterations=1)

    assert result["status"] == "max_iterations_reached"


def test_agent_loop_rejects_repeated_state():
    repeated_action = Action(tool_name="get_product", arguments={"product_id": "P1001"})
    runner = AgentRunner(llm_client=ScriptedLLMClient([repeated_action, repeated_action]))
    goal = Goal(text="Describe a product")

    result = runner.run(goal, max_iterations=3)

    assert result["status"] == "failed"
    assert "repeated observations" in result["final_answer"]


def test_agent_loop_does_not_finish_without_evidence():
    runner = AgentRunner(
        llm_client=ScriptedLLMClient([Action(tool_name="finish", arguments={})])
    )

    result = runner.run(Goal(text="Find a product under 5000 INR in stock"))

    assert result["status"] == "failed"
    assert result["observations"] == []
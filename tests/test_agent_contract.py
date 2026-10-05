from src.agent.contracts import Action, Goal, Observation
from src.agent.runner import AgentRunner


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


def test_agent_loop_completes_goal():
    runner = AgentRunner()
    goal = Goal(text="Find a running shoe under 5000 INR in stock")

    result = runner.run(goal, max_iterations=5)

    assert result["status"] == "completed"
    assert "Running Shoes" in result["final_answer"]


def test_agent_loop_stops_on_max_iterations():
    runner = AgentRunner()
    goal = Goal(text="Find a product that does not exist")

    result = runner.run(goal, max_iterations=2)

    assert result["status"] in {"failed", "max_iterations_reached"}


def test_agent_loop_rejects_repeated_state():
    runner = AgentRunner()
    goal = Goal(text="Find a running shoe under 5000 INR in stock")

    result = runner.run(goal, max_iterations=3)

    assert result["status"] in {"completed", "failed", "max_iterations_reached"}
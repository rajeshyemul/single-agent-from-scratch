from src.agent.contracts import Goal
from src.agent.runner import AgentRunner


def main():
    goal_text = input("Enter your goal: ").strip()
    if not goal_text:
        print("Please enter a goal.")
        return

    result = AgentRunner().run(Goal(text=goal_text))
    print(f"\n[{result['status']}] {result['final_answer']}")


if __name__ == "__main__":
    main()
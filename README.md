# 04-single-agent-from-scratch

[![Python 3.13](https://img.shields.io/badge/Python-3.13-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Local LLM: Ollama](https://img.shields.io/badge/LLM-Ollama%20local-black?logo=ollama&logoColor=white)](https://ollama.com/)
[![Tests: pytest](https://img.shields.io/badge/tests-pytest-0A9EDC?logo=pytest&logoColor=white)](https://pytest.org/)

A minimal single-agent learning project built from scratch to teach the core idea of an agent loop.

## Overview

This project demonstrates the difference between:
- a simple tool-calling app
- and a true agent loop

The key teaching point is this:
- the agent decides what to do next
- the application validates the proposed action
- the application executes the real tool
- the real result becomes an observation
- the agent decides again based on that observation
- the loop continues until the goal is satisfied or a safety rule stops it

## Learning objective

We are not building a production agent framework.
We are building the smallest possible working loop so the underlying pattern is easy to understand.

The repo teaches the following architecture:

Goal

↓

Agent proposes action

↓

Application validates action

↓

Application executes tool

↓
Observation is returned

↓

Agent decides next action

↓

Continue until completion or stop condition

## What is implemented in this version

This version includes:
- a Goal contract
- an Action contract
- an Observation contract
- a FinalAnswer contract
- a minimal runner loop
- fake product tools
- validation for action safety
- loop termination check
- max-iteration protection
- repeated-observation protection
- grounded final answer generation based on real tool output

## Stage B: local Ollama model

The current working tree uses a locally running Ollama model to choose the next action. No OpenAI API key or cloud LLM service is used.

Stage A was the deterministic baseline. Its original implementation is preserved in the `v1.0.0` Git tag; the current working tree is the Stage B Ollama implementation.

The model only proposes an action. The application validates the response, executes the selected product tool, records the observation, and checks the evidence before completing the goal.

## Product domain

This project uses a small fake e-commerce catalog:

- P1001 → Running Shoes → ₹4,999 → stock 12
- P1002 → Yoga Mat → ₹1,499 → stock 40
- P1003 → Backpack → ₹2,299 → stock 18

## Architecture

### Contracts
The central schema is defined in:
- src/agent/contracts.py

It contains:
- Goal
- Action
- Observation
- FinalAnswer
- AgentStep

### Tools
The tool layer is defined in:
- src/tools/product_tools.py
- src/tools/validation.py

The tools are intentionally small and explicit:
- get_product
- get_product_price
- check_inventory
- finish is used as a terminal action by the agent

### Runner
The execution boundary and loop live in:
- src/agent/runner.py

The runner is responsible for:
- calling the agent decision policy
- validating the action
- executing the real tool
- capturing observations
- deciding whether to finish or continue
- stopping on safety constraints

### LLM layer
The local model integration is implemented in:
- src/llm/client.py
- src/llm/prompts.py
- src/llm/schema.py

The prompt provides the goal, product catalog, available actions, and observations. Ollama returns a schema-constrained JSON action, which is parsed and validated before the runner can execute it.

## Minimal loop behavior

A typical query is:

> Find a running shoe under 5000 INR in stock

The loop behaves like this:

1. Goal is created.
2. Ollama proposes one action using the goal and observations so far.
3. The app validates the action and executes the selected product tool.
4. The tool result is stored as an observation and supplied to Ollama on the next decision.
5. The app completes only when its evidence checks satisfy the supported goal conditions; otherwise it continues or stops safely.

### Install and run

1. Install [Ollama](https://ollama.com/download) and download the default model:

	```bash
	ollama pull llama3.2:latest
	```

2. Start Ollama using the desktop application, or run `ollama serve` if the service is not already running.

3. Create and activate a Python environment, then install project dependencies:

	```bash
	python3 -m venv .venv
	source .venv/bin/activate
	python -m pip install -r requirements.txt
	```

4. Optionally choose a different locally available model or Ollama host:

	```bash
	export OLLAMA_MODEL="llama3.2:latest"
	export OLLAMA_HOST="http://localhost:11434"
	```

5. Run a sample goal from the repository root:

	```bash
	python -c 'from src.agent.contracts import Goal; from src.agent.runner import AgentRunner; result = AgentRunner().run(Goal("Find a running shoe under 5000 INR in stock")); print(result["final_answer"])'
	```

The first run requires the selected model to be available in Ollama. Change `OLLAMA_MODEL` to another model already pulled locally if desired.

## Safety rules implemented

This repo includes several safety behaviors:
- unknown tools are rejected
- missing required arguments are rejected
- malformed actions are rejected
- finish is allowed only when the goal is truly satisfied
- max iteration guard prevents infinite loops
- repeated observation states trigger a stop to avoid looping
- final answer generation depends on real observed values

## Current scope

This project intentionally does not include:
- LangGraph
- memory layers
- multi-agent orchestration
- MCP integration
- production planning systems
- long-term context memory
- hosting or managing the Ollama service

## Project structure

```text
04-single-agent-from-scratch/
├── README.md
├── requirements.txt
├── .gitignore
├── main.py
├── data/
│   └── products.json
├── src/
│   ├── __init__.py
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── contracts.py
│   │   └── runner.py
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── product_tools.py
│   │   └── validation.py
│   └── llm/
│       ├── __init__.py
│       ├── client.py
│       ├── prompts.py
│       └── schema.py
├── tests/
│   ├── __init__.py
│   └── test_agent_contract.py
└── .venv/
```

## Validation

Run the test suite with:

```bash
python -m pytest -q
```

The test suite uses controlled Ollama responses and scripted actions, so it does not require a running Ollama service or model.

## Summary

This repo is a working minimal single-agent loop that teaches the exact core pattern:

Goal → Action → Observation → Decision → Repeat → Finish

It is intentionally small, explicit, and easy to understand. Stage A's deterministic baseline is preserved in Git history; Stage B adds local model-backed action selection without allowing the model to execute tools directly.

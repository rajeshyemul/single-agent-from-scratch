# 04-single-agent-from-scratch

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

## Important note: this is deterministic, not a real LLM call

This repository does not yet integrate with an actual model provider such as OpenAI, Anthropic, Azure OpenAI, or Ollama.

The decision logic is intentionally deterministic and rule-based.
It simulates the agent decision step using simple logic, without calling a real LLM.

This is intentional for learning clarity.

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

### LLM layer placeholder
The decision policy is currently implemented in:
- src/llm/client.py

This file behaves like a minimal policy engine, but it is not a real external LLM integration.

## Minimal loop behavior

A typical query is:

> Find a running shoe under 5000 INR in stock

The loop behaves like this:

1. Goal is created.
2. The agent decides to fetch product P1001.
3. The app validates the action.
4. The app executes get_product("P1001").
5. The result is stored as an observation.
6. The agent checks whether the result satisfies the goal.
7. If price is under budget, it checks inventory.
8. If stock is positive and the goal is met, the agent finishes.
9. If the goal cannot be met, or the loop is unsafe, the agent exits with a failure or max-iteration state.

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
- real model API integration

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
│       └── client.py
├── tests/
│   ├── __init__.py
│   └── test_agent_contract.py
└── .venv/
```

## Validation

Run the test suite with:

```bash
cd /path/to/04-single-agent-from-scratch
python3 -m pytest -q
```

Current status:
- 7 tests passing

## Summary

This repo is a working minimal single-agent loop that teaches the exact core pattern:

Goal → Action → Observation → Decision → Repeat → Finish

It is intentionally small, explicit, and easy to understand.
It is a solid foundation for the next step, where a real model-backed agent can replace the deterministic policy with actual LLM-driven action selection.

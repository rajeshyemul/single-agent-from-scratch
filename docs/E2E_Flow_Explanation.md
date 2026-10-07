The most important thing I want you to understand is this:

> **Our agent is a loop where Ollama makes a decision, but Python owns the execution, evidence, and stopping rules.**

That one sentence explains almost the entire project.

---

# 1. First, forget the code for a moment

Imagine you are the user.

You say:

> **"Find a running shoe under 5000 INR in stock."**

Our system has:

```text
User Goal
   ↓
Agent
   ↓
LLM decides what to do
   ↓
Python validates decision
   ↓
Python executes tool
   ↓
Tool returns factual result
   ↓
Result becomes Observation
   ↓
Observation goes back to LLM
   ↓
LLM decides what to do next
   ↓
...
   ↓
Enough evidence?
   ↓
Final Answer
```

The important distinction is:

```text
LLM = DECISION MAKER

Python Runner = CONTROLLER / EXECUTOR

Tools = ACTUAL WORK

Observations = FACTS RETURNED BY WORK
```

---

# 2. Our actual architecture


```text
04-single-agent-from-scratch
│
├── data/
│   └── products.json
│
├── src/
│   │
│   ├── agent/
│   │   ├── contracts.py
│   │   └── runner.py
│   │
│   ├── llm/
│   │   ├── client.py
│   │   ├── prompts.py
│   │   └── schema.py
│   │
│   └── tools/
│       ├── product_tools.py
│       └── validation.py
│
└── tests/
    └── test_agent_contract.py
```

Each layer has a very specific responsibility.

| Component | Responsibility |
|---|---|
| `Goal` | Represents user's objective |
| `LLMClient` | Asks Ollama what to do next |
| `prompts.py` | Builds the context sent to Ollama |
| `schema.py` | Defines what Ollama is allowed to return |
| `validation.py` | Checks whether proposed action is legal |
| `product_tools.py` | Actually performs product operations |
| `Observation` | Stores tool results |
| `AgentRunner` | Controls the entire loop |
| `FinalAnswer` | Represents the final response |

This separation is actually very good for learning agent architecture.

---

# 3. Let's take one real example

Our catalog contains:

```text
P1001 → Running Shoes → ₹4,999 → stock 12
P1002 → Yoga Mat     → ₹1,499 → stock 40
P1003 → Backpack     → ₹2,299 → stock 18
```

These are actually stored in `products.json`.

So imagine the user says:

```text
Find a running shoe under 5000 INR in stock
```

The application creates:

```python
Goal(
    text="Find a running shoe under 5000 INR in stock"
)
```

This is the starting point.

---

# 4. What exactly happens when `AgentRunner.run()` starts?

The entry point to the **agent loop** is:

```python
runner.run(goal)
```

Inside our runner:

```python
def run(self, goal: Goal, max_iterations: int = 5):
    observations: list[Observation] = []

    for iteration in range(max_iterations):
        ...
```

So the first thing it does is:

```text
Goal
 +
Empty observations
```

Conceptually:

```text
GOAL:
Find a running shoe under 5000 INR in stock

OBSERVATIONS:
[]

ITERATION:
0
```

This is important.

The agent has the **goal**, but it doesn't yet have any evidence.

This does not mean `python main.py` currently starts the agent. `main.py` is still a placeholder. To run the agent today, create a `Goal` and call `AgentRunner().run(goal)`, as shown in the README's run example.

---

# 5. Then the Runner asks the LLM

The next important line is:

```python
next_action = self.llm_client.decide_next_action(
    goal,
    observations
)
```

This means:

> "Ollama, given the goal and everything we currently know, tell me what action should happen next."

Notice something very important:

### The runner does NOT say:

```text
Call get_product()
```

Instead it asks the LLM. The key difference from a one-shot tool call is that the runner can feed observations back into a later decision if the goal is still incomplete.

---

# 6. What does `decide_next_action()` actually do?

Our `LLMClient` calls:

```python
messages = build_decision_messages(
    goal,
    observations,
    products=get_all_products(),
)
```

So before calling Ollama, it collects **three major pieces of information**:

```text
1. Goal
2. Previous observations
3. Product catalog
```

For our example:

```text
Goal:
Find a running shoe under 5000 INR in stock

Product catalog:
P1001 Running Shoes ₹4999 stock 12
P1002 Yoga Mat ₹1499 stock 40
P1003 Backpack ₹2299 stock 18

Observations:
None
```

This is then converted into the messages in `prompts.py`.

Important distinction: the catalog is context supplied to help Ollama choose an action; it is not added to the runner's `observations`. The completion checker requires relevant tool results in the observations before it accepts `finish`.

---

# 7. This is where the LLM gets its "context"

Our system message basically tells Ollama:

> You are selecting the next action.

And importantly:

> **Never claim that a tool has run; the application will execute the selected action.**

That's a very important boundary in our design.

The model is being told:

```text
You decide.

Python executes.
```

Our prompt also tells it:

```text
Available tools:

get_product
get_product_price
check_inventory
finish
```

So the LLM knows its action vocabulary.

---

# 8. What does Ollama actually return?

Suppose Ollama decides:

```json
{
  "tool_name": "get_product",
  "arguments": {
    "product_id": "P1001"
  }
}
```

This is **not yet a Python function call**.

This is simply a message from the LLM saying:

> "I propose that you execute `get_product` with P1001."

This distinction is fundamental.

---

# 9. Think of it like a manager and employee

Imagine:

```text
LLM = Manager

Python Runner = Operations Team
```

Manager says:

> "Please check product P1001."

Manager doesn't physically access the database.

Operations team does it.

Similarly:

```text
LLM
 │
 │ Action:
 │ get_product(P1001)
 ↓
Python Runner
 │
 │ actually calls
 ↓
get_product("P1001")
```

That is exactly our architecture.

---

# 10. Now comes `schema.py`

We have:

```python
ACTION_RESPONSE_SCHEMA
```

This defines the shape Ollama is expected to produce.

For example:

```json
{
  "tool_name": "get_product",
  "arguments": {
    "product_id": "P1001"
  }
}
```

Or:

```json
{
  "tool_name": "finish",
  "arguments": {}
}
```

The schema tells the model:

> These are the kinds of responses I accept.

It also defines the valid tools:

```text
get_product
get_product_price
check_inventory
finish
```

So this is the first protection layer.

---

# 11. But why do we need validation if we already have schema?

This is an excellent agent architecture question.

Because:

> **LLM output is untrusted.**

Even though you tell Ollama to produce a specific schema, your Python application should not blindly execute whatever comes back.

That's why your code does:

```python
if not validate_action(action):
    raise ValueError(...)
```

And then `runner.py` validates again.

So we have:

```text
LLM
 ↓
Schema constraint
 ↓
JSON parsing
 ↓
Action object
 ↓
Application validation
 ↓
Execution
```

That is defense in depth.

---

# 12. What does `validation.py` protect us from?

Suppose Ollama returns:

```json
{
  "tool_name": "delete_database",
  "arguments": {}
}
```

our system says:

```text
Is delete_database an allowed tool?
```

No.

Rejected.

Or:

```json
{
  "tool_name": "get_product",
  "arguments": {}
}
```

Rejected because:

```text
get_product requires product_id
```

Or:

```json
{
  "tool_name": "get_product",
  "arguments": {
    "product_id": 1001
  }
}
```

Rejected because:

```text
product_id must be a string
```

Our validation layer therefore creates the **execution boundary**.

---

# 13. Now the actual tool executes

Suppose the action is valid:

```python
Action(
    tool_name="get_product",
    arguments={"product_id": "P1001"}
)
```

The runner has this mapping:

```python
tool_map = {
    "get_product": get_product,
    "get_product_price": get_product_price,
    "check_inventory": check_inventory,
}
```

So:

```text
"get_product"
       ↓
get_product()
```

The runner executes:

```python
tool_fn(**action.arguments)
```

which effectively becomes:

```python
get_product(product_id="P1001")
```

Now Python actually performs the work.

---

# 14. The tool reads the real data

`product_tools.py` opens:

```text
data/products.json
```

It finds:

```json
{
  "product_id": "P1001",
  "name": "Running Shoes",
  "category": "Footwear",
  "price": 4999,
  "currency": "INR",
  "stock": 12
}
```

And returns it.

This is now a **real factual result** from our application.

Not something hallucinated by the LLM.

---

# 15. This becomes an Observation

The runner then does:

```python
new_observation = Observation(
    result=execution["result"],
    source="tool"
)

observations.append(new_observation)
```

This is a very important transformation:

```text
ACTION
   ↓
Tool executes
   ↓
Tool Result
   ↓
Observation
```

For example:

```python
Observation(
    result={
        "product_id": "P1001",
        "name": "Running Shoes",
        "category": "Footwear",
        "price": 4999,
        "currency": "INR",
        "stock": 12
    },
    source="tool"
)
```

---

# 16. Why call it an Observation?

Because the agent has now **observed something about the world**.

Before the tool:

```text
Agent doesn't know:
Is P1001 available?
What is its price?
```

After the tool:

```text
Agent knows:
P1001 = Running Shoes
price = ₹4999
stock = 12
```

So:

```text
Action = "I want to find out something."

Observation = "Here is what I found out."
```

---

# 17. Now the magic happens: the loop goes back to Ollama

This is the most important difference between a tool-calling application and an agent.

After getting an observation, the runner checks whether the evidence already satisfies the goal. **Only if it does not** will the loop ask Ollama for another action.

If the goal is still incomplete, the next decision includes the observation. For example, if the first tool had returned only the product name:

```text
Observation:
P1001 Running Shoes
```

For this project’s product goal, the observation from `get_product()` contains both price and stock, so the common run completes here rather than asking Ollama again. The next decision happens only when the evidence is still incomplete.

When another decision is needed, the runner goes back here:

```python
next_action = self.llm_client.decide_next_action(
    goal,
    observations
)
```

In that incomplete case, Ollama gets:

```text
Goal:
Find a running shoe under 5000 INR in stock

Previous observation:
P1001 Running Shoes
price 4999
stock 12
```

And Ollama must decide:

> "What should I do now?"

---

# 18. This is the actual agent behavior

This is the part I really want you to internalize.

It is:

```text
             ┌─────────────┐
             │    GOAL     │
             └──────┬──────┘
                    ↓
             ┌─────────────┐
             │     LLM     │
             │   DECIDES   │
             └──────┬──────┘
                    ↓
             ┌─────────────┐
             │    ACTION   │
             └──────┬──────┘
                    ↓
             ┌─────────────┐
             │   PYTHON    │
             │  EXECUTES   │
             └──────┬──────┘
                    ↓
             ┌─────────────┐
             │ OBSERVATION │
             └──────┬──────┘
                    ↓
             ┌─────────────┐
             │  EVIDENCE   │
             │ COMPLETE?   │
             └──────┬──────┘
                    ├── YES → FINAL ANSWER
                    └── NO  → LLM DECIDES AGAIN
```

**That loop is the agent.**

Our README describes this same architecture as:

> Goal → Action → Observation → Decision → Repeat → Finish.

---

# 19. But there is something interesting about our current implementation

Our example goal can actually be completed from the first `get_product()` result because our product record already contains:

```text
price = 4999
stock = 12
```

our `goal_is_complete()` combines facts by product ID.

So:

```text
P1001
 ├── price = 4999
 └── stock = 12
```

satisfies:

```text
price <= 5000
AND
stock > 0
```

Therefore:

```text
Evidence complete?
       ↓
      YES
       ↓
Final Answer
```

For the example goal, the exact runtime sequence is typically:

```text
Goal
 ↓
Ollama
 ↓
get_product(P1001)
 ↓
Tool
 ↓
Observation:
Running Shoes / ₹4999 / stock 12
 ↓
Evidence checker
 ↓
YES
 ↓
Final Answer
```

The runner checks evidence immediately after adding the observation, so this common path finishes after one tool action: there is no second Ollama call in this case. Multiple model/tool rounds occur only when the observations do not yet satisfy the goal.

The completion checker currently supports a narrow set of goal patterns: it recognizes a price requirement when the goal contains both “under” and “5000”, and a stock requirement when the goal contains “stock”. It checks those conditions against observations for the same product ID. It does not yet interpret arbitrary budgets or general natural-language requirements; goals outside these patterns will not be marked complete.

---

# 20. So why do we have `get_product_price` and `check_inventory`?

These tools are available for **focused lookups** too. The following is a hypothetical example of how the loop could behave if product details were returned separately; it is not the current catalog behavior, because `get_product()` currently returns the full product record.

For example, imagine `get_product()` didn't provide price.

Then:

```text
Goal
 ↓
LLM
 ↓
get_product(P1001)
 ↓
Observation:
Running Shoes
 ↓
LLM sees:
"I still don't know price"
 ↓
LLM
 ↓
get_product_price(P1001)
 ↓
Observation:
₹4999
 ↓
LLM
 ↓
check_inventory(P1001)
 ↓
Observation:
stock 12
 ↓
Complete
```

This illustrates how multiple action/observation rounds can happen when one result is not enough.

Our current implementation supports combining observations from different calls by `product_id`.

---

# 21. This is where our `AgentStep` becomes conceptually useful

Our contract contains:

```python
@dataclass
class AgentStep:
    goal: Goal
    observations: List[Observation] = field(default_factory=list)
    proposed_action: Optional[Action] = None
    final_answer: Optional[FinalAnswer] = None
```

Think of `AgentStep` as a **snapshot of the agent's current situation**.

For example:

### Step 1

```text
Goal:
Find running shoe under ₹5000 in stock

Observations:
[]

Proposed action:
get_product(P1001)

Final answer:
None
```

### Step 2

```text
Goal:
Find running shoe under ₹5000 in stock

Observations:
[
  P1001 = Running Shoes
]

Proposed action:
check_inventory(P1001)

Final answer:
None
```

### Step 3

```text
Goal:
Find running shoe under ₹5000 in stock

Observations:
[
  P1001 = Running Shoes
  price = 4999
  stock = 12
]

Proposed action:
finish()

Final answer:
Running Shoes are available for ₹4999.
```

Our current `runner.py` doesn't actually use `AgentStep` to drive the loop; it keeps `observations` directly. So treat `AgentStep` as a **contract prepared for representing a step**, not as the object currently orchestrating every iteration.

That's an important distinction.

---

# 22. Now let's understand `finish`

This is another very important concept.

The LLM can propose:

```json
{
  "tool_name": "finish",
  "arguments": {}
}
```

This means:

> "I believe the task is finished."

But our application does **not** blindly trust that.

Our runner checks:

```python
if next_action.tool_name == "finish":
```

Then:

```python
if self.llm_client.goal_is_complete(goal, observations):
```

Only if the evidence supports completion does it return:

```text
completed
```

Otherwise:

```text
failed
```

This gives us:

```text
LLM says:
"Finished!"

        ↓

Application asks:
"Do we actually have evidence?"

        ↓

YES → complete
NO  → reject
```

That is a very important agentic safety principle.

---

# 23. This is actually one of the strongest parts of our design

We have separated:

### Agent decision

```text
"Should I finish?"
```

from:

### Evidence validation

```text
"Is the goal actually satisfied?"
```

This prevents:

```text
LLM:
"I found a shoe under ₹5000."

Application:
"Show me the evidence."

LLM:
"Trust me."
```

No.

Our system says:

```text
Show me observations.
```

And only real observations can establish completion.

This is directly aligned with the project's grounded-answer design: final output depends on observed values rather than unsupported model claims.

---

# 24. Where does the final answer come from?

Once the evidence is sufficient:

```python
final_answer = self.llm_client.build_final_answer(
    goal,
    observations
)
```

The implementation combines facts from the observations and creates something like:

```text
I found Running Shoes with price ₹4999 and stock 12.
This satisfies the goal.
```

Notice something interesting:

The final answer is based on:

```text
Observation
```

not:

```text
LLM imagination
```

That's important.

---

# 25. Now let's understand the complete real execution

Let's simulate our exact project.

## User

```text
Find a running shoe under 5000 INR in stock
```

### Step 1 — Create Goal

```python
Goal(
    text="Find a running shoe under 5000 INR in stock"
)
```

---

### Step 2 — Runner starts

```text
observations = []
```

---

### Step 3 — Runner asks Ollama

```text
Goal:
Find a running shoe under 5000 INR in stock

Observations:
None

Catalog:
P1001 Running Shoes ₹4999 stock 12
P1002 Yoga Mat ₹1499 stock 40
P1003 Backpack ₹2299 stock 18
```

---

### Step 4 — Ollama decides

Potential response:

```json
{
  "tool_name": "get_product",
  "arguments": {
    "product_id": "P1001"
  }
}
```

---

### Step 5 — Python parses it

```python
Action(
    tool_name="get_product",
    arguments={"product_id": "P1001"}
)
```

---

### Step 6 — Python validates

Checks:

```text
Is Action valid?
         ↓
Is get_product allowed?
         ↓
Is product_id present?
         ↓
Is product_id a string?
         ↓
YES
```

---

### Step 7 — Python executes

```python
get_product(product_id="P1001")
```

---

### Step 8 — Tool reads catalog

Returns:

```json
{
  "product_id": "P1001",
  "name": "Running Shoes",
  "category": "Footwear",
  "price": 4999,
  "currency": "INR",
  "stock": 12
}
```

---

### Step 9 — Create Observation

```python
Observation(
    result={
        "product_id": "P1001",
        "name": "Running Shoes",
        "price": 4999,
        "stock": 12
    },
    source="tool"
)
```

---

### Step 10 — Evidence checker

Checks:

```text
Price:
4999 <= 5000
        ↓
       YES

Stock:
12 > 0
        ↓
       YES
```

Therefore:

```text
Goal satisfied
```

---

### Step 11 — Build answer

```text
I found Running Shoes with price ₹4999 and stock 12.
This satisfies the goal.
```

---

### Step 12 — Return

```json
{
  "status": "completed",
  "final_answer": "I found Running Shoes with price ₹4999 and stock 12. This satisfies the goal.",
  "observations": [...]
}
```

Done.

---

# 26. Compare a single tool call with this agent loop

## Tool Calling

```text
User
 ↓
LLM
 ↓
Tool
 ↓
Result
 ↓
LLM
 ↓
Answer
```

This is a simple illustrative pattern: one tool result is returned to the LLM, which then prepares an answer. Tool-calling systems can also loop; the distinction here is that our runner explicitly manages repeated decisions, observations, evidence checks, and stopping rules.

---

# 27. What happens if Ollama gives a bad answer?

Our architecture handles several failure cases.

### Case 1 — Ollama unavailable

```text
Runner
 ↓
Ollama
 ↓
Connection error
```

Result:

```text
failed
```

Our tests explicitly cover this.

---

### Case 2 — Invalid JSON

Ollama returns:

```text
Hello, I found a shoe.
```

Instead of:

```json
{
  "tool_name": "...",
  "arguments": {}
}
```

Our client rejects it.

---

### Case 3 — Unknown tool

```json
{
  "tool_name": "delete_customer",
  "arguments": {}
}
```

Rejected.

---

### Case 4 — Missing argument

```json
{
  "tool_name": "get_product",
  "arguments": {}
}
```

Rejected.

---

### Case 5 — Wrong type

```json
{
  "tool_name": "get_product",
  "arguments": {
    "product_id": 1001
  }
}
```

Rejected.

Our tests explicitly cover malformed responses and invalid action shapes.

---

# 28. What happens if the agent gets stuck?

We have:

```python
max_iterations=5
```

So the system effectively says:

> "Agent, you get at most five chances."

For example:

```text
Iteration 1 → get_product
Iteration 2 → get_product
Iteration 3 → get_product
Iteration 4 → get_product
Iteration 5 → get_product
```

If it never reaches completion:

```text
max_iterations_reached
```

This is a basic but very important **agent safety mechanism**.

Without it:

```text
LLM
 ↓
Action
 ↓
Observation
 ↓
LLM
 ↓
Action
 ↓
Observation
 ↓
...
```

could theoretically continue forever.

---

# 29. We also have repeated-observation protection

Our runner checks the last two observations.

If:

```text
Observation 1:
P1001

Observation 2:
P1001
```

are identical, it stops.

Why?

Because perhaps the LLM is doing:

```text
get_product(P1001)
get_product(P1001)
get_product(P1001)
...
```

That's a loop.

So we have:

```text
Maximum iterations
+
Repeated observation detection
```

Two basic loop-protection mechanisms.

---

# 30. Now let's understand the role of `temperature=0`

Our Ollama call contains:

```python
options={"temperature": 0}
```

For this learning project, that's useful because we want the model's decision-making to be as deterministic as possible.

Conceptually:

```text
Same goal
+
Same context
+
Same model
+
temperature 0
        ↓
more predictable action selection
```

It doesn't guarantee perfect determinism in every system/model configuration, but it reduces randomness.

For an agent-learning exercise, that's useful because we are trying to understand:

> "Why did the agent choose this action?"

rather than:

> "Why did it randomly choose something different this time?"

---

# 31. Now the most important architectural boundary

```text
                 LLM
                  │
                  │ proposes
                  ↓
                Action
                  │
                  │ validate
                  ↓
             Application
                  │
                  │ execute
                  ↓
                Tool
                  │
                  │ result
                  ↓
             Observation
                  │
                  │ context
                  ↓
                 LLM
```

The LLM **never directly owns execution**.

That's the reason your system is controllable.

---

# 32. What is actually "agentic" here?

Not:

```text
Ollama
```

Ollama itself is just your local model runtime.

Not:

```text
Action
```

That's just data.

Not:

```text
Tool
```

That's just a function.

Not:

```text
Runner
```

by itself.

The agentic behavior emerges from the combination:

```text
LLM decision
+
Action
+
Execution
+
Observation
+
Feedback
+
Repeated decision
+
Termination
```

In other words:

> **The loop is the agent.**

---

# 33. And this is why we shouldn't add LangGraph yet

If we used a framework right now, we might write something like:

```text
Graph
 ├── LLM Node
 ├── Tool Node
 ├── Validation Node
 ├── Observation Node
 └── Finish Node
```

But then we could easily think:

> "LangGraph is the agent."

It isn't.

LangGraph would simply **orchestrate the same conceptual flow** we are manually implementing now.

---

# 34. Our entire project in one sentence

If an interviewer asks:

> **"Explain the architecture of your single-agent implementation."**

we can say:

> "The system receives a goal, sends the goal and accumulated observations to a local LLM, receives a structured action proposal, validates that action at the application boundary, executes the corresponding Python tool, converts the tool result into an observation, feeds that observation back to the LLM for the next decision, and continues until evidence satisfies the goal or a safety condition such as maximum iterations or repeated state stops the loop."

That is a strong technical explanation.

---

# 35. And the mental model I want us to retain

Don't memorize all the files.

Remember this:

```text
                    USER
                      │
                      │ Goal
                      ↓
                ┌───────────┐
                │    LLM    │
                │  DECIDES  │
                └─────┬─────┘
                      │
                      │ Action
                      ↓
                ┌───────────┐
                │ VALIDATOR │
                └─────┬─────┘
                      │
                      ↓
                ┌───────────┐
                │   TOOL    │
                │  EXECUTES │
                └─────┬─────┘
                      │
                      │ Result
                      ↓
                ┌───────────┐
                │OBSERVATION│
                └─────┬─────┘
                      │
                      │ Context
                      ↓
                ┌───────────┐
                │    LLM    │
                │  DECIDES  │
                │   AGAIN   │
                └─────┬─────┘
                      │
                      ↓
                    ...
                      │
                      ↓
                ┌───────────┐
                │  EVIDENCE │
                │ COMPLETE? │
                └─────┬─────┘
                  YES  │
                       ↓
                ┌───────────┐
                │  ANSWER   │
                └───────────┘
```

And the four words to remember are:

> **Goal → Action → Observation → Decision**

repeated while the evidence is incomplete, until one of these outcomes occurs:

> **Evidence is sufficient → Final Answer**

or a safety condition stops the run, such as an invalid action, an Ollama error, a repeated observation, or the maximum iteration limit.
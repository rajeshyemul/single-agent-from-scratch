from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Goal:
    text: str


@dataclass
class Action:
    tool_name: str
    arguments: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Observation:
    result: Any
    source: str = "tool"


@dataclass
class FinalAnswer:
    text: str


@dataclass
class AgentStep:
    goal: Goal
    observations: List[Observation] = field(default_factory=list)
    proposed_action: Optional[Action] = None
    final_answer: Optional[FinalAnswer] = None

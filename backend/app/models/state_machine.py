from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Set


class States:
    IDLE = "idle"
    REGISTERING = "registering"
    ORDERING = "ordering"
    CONFIRMING_ORDER = "confirming_order"
    ADDING_INVENTORY = "adding_inventory"
    CONFIRMING_INVENTORY = "confirming_inventory"
    QUERYING = "querying"


@dataclass
class StateMachine:
    state: str = States.IDLE

    def __post_init__(self):
        self._transitions: Dict[str, Set[str]] = {
            States.IDLE: {States.REGISTERING, States.ORDERING, States.ADDING_INVENTORY, States.QUERYING},
            States.REGISTERING: {States.IDLE, States.ORDERING, States.ADDING_INVENTORY, States.QUERYING},
            States.ORDERING: {States.CONFIRMING_ORDER, States.IDLE},
            States.CONFIRMING_ORDER: {States.IDLE},
            States.ADDING_INVENTORY: {States.CONFIRMING_INVENTORY, States.IDLE},
            States.CONFIRMING_INVENTORY: {States.IDLE},
            States.QUERYING: {States.IDLE},
        }

    def can_transition(self, to_state: str) -> bool:
        allowed = self._transitions.get(self.state, set())
        return to_state in allowed

    def transition(self, to_state: str) -> None:
        if not self.can_transition(to_state):
            raise ValueError(f"Invalid transition: {self.state} -> {to_state}")
        self.state = to_state


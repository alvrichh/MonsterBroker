"""Where the agent keeps what it did: the whole AgentState as one JSON file."""

from __future__ import annotations

from pathlib import Path

from app.utils.helpers import read_json, write_json

from .state import AgentState, Decision

MAX_DECISIONS = 500


class Memory:
    def __init__(self, path: Path, initial: AgentState) -> None:
        self._path = path
        self._initial = initial

    def load(self) -> AgentState:
        raw = read_json(self._path, None)
        if raw is None:
            return self._initial.model_copy(deep=True)
        try:
            return AgentState.model_validate(raw)
        except ValueError:
            # A state file from an older shape: start over rather than crash.
            return self._initial.model_copy(deep=True)

    def save(self, state: AgentState) -> None:
        write_json(self._path, state.model_dump(mode="json"))

    def remember(self, state: AgentState, decision: Decision) -> None:
        state.decisions.append(decision)
        del state.decisions[:-MAX_DECISIONS]

    def reset(self) -> AgentState:
        state = self._initial.model_copy(deep=True)
        self.save(state)
        return state

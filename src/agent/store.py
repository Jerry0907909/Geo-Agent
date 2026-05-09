"""轻量级 Agent Run 状态存储。"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from threading import Lock
from typing import Dict, Optional

from src.agent.schemas import AgentRunStatus, AgentSessionState


@dataclass
class StoredAgentRun:
    """内存态 run 记录。"""

    owner_id: int
    state: AgentSessionState


class AgentRunStore:
    """线程安全的内存 run store。"""

    def __init__(self) -> None:
        self._runs: Dict[str, StoredAgentRun] = {}
        self._active_runs_by_owner: Dict[int, set[str]] = {}
        self._lock = Lock()

    def save(self, owner_id: int, state: AgentSessionState, *, active: Optional[bool] = None) -> AgentSessionState:
        with self._lock:
            self._runs[state.run_id] = StoredAgentRun(owner_id=owner_id, state=deepcopy(state))
            self._sync_active_state(owner_id, state, active=active)
            return deepcopy(state)

    def get(self, run_id: str, owner_id: Optional[int] = None) -> Optional[AgentSessionState]:
        with self._lock:
            stored = self._runs.get(run_id)
            if stored is None:
                return None
            if owner_id is not None and stored.owner_id != owner_id:
                return None
            return deepcopy(stored.state)

    def cancel(self, run_id: str, owner_id: int) -> Optional[AgentSessionState]:
        with self._lock:
            stored = self._runs.get(run_id)
            if stored is None or stored.owner_id != owner_id:
                return None
            if stored.state.status in {
                AgentRunStatus.COMPLETED,
                AgentRunStatus.FAILED,
                AgentRunStatus.CANCELLED,
            }:
                return deepcopy(stored.state)
            stored.state.status = AgentRunStatus.CANCELLED
            stored.state.updated_at = datetime.utcnow()
            self._sync_active_state(owner_id, stored.state, active=True)
            return deepcopy(stored.state)

    def start_run(
        self,
        owner_id: int,
        state: AgentSessionState,
        *,
        max_concurrent: int = 1,
    ) -> bool:
        with self._lock:
            active_runs = self._active_runs_by_owner.setdefault(owner_id, set())
            if len(active_runs) >= max_concurrent:
                return False
            self._runs[state.run_id] = StoredAgentRun(owner_id=owner_id, state=deepcopy(state))
            active_runs.add(state.run_id)
            return True

    def finish_run(self, owner_id: int, state: AgentSessionState) -> AgentSessionState:
        with self._lock:
            self._runs[state.run_id] = StoredAgentRun(owner_id=owner_id, state=deepcopy(state))
            self._active_runs_by_owner.setdefault(owner_id, set()).discard(state.run_id)
            return deepcopy(state)

    def is_cancel_requested(self, run_id: str) -> bool:
        with self._lock:
            stored = self._runs.get(run_id)
            return stored is not None and stored.state.status == AgentRunStatus.CANCELLED

    def active_run_ids(self, owner_id: int) -> list[str]:
        with self._lock:
            return sorted(self._active_runs_by_owner.get(owner_id, set()))

    def _sync_active_state(
        self,
        owner_id: int,
        state: AgentSessionState,
        *,
        active: Optional[bool],
    ) -> None:
        active_runs = self._active_runs_by_owner.setdefault(owner_id, set())
        if active is True:
            active_runs.add(state.run_id)
            return
        if active is False:
            active_runs.discard(state.run_id)
            return
        if state.status in {
            AgentRunStatus.QUEUED,
            AgentRunStatus.PLANNING,
            AgentRunStatus.RUNNING,
            AgentRunStatus.CANCELLED,
        }:
            active_runs.add(state.run_id)
            return
        active_runs.discard(state.run_id)


_RUN_STORE: Optional[AgentRunStore] = None


def get_agent_run_store() -> AgentRunStore:
    global _RUN_STORE
    if _RUN_STORE is None:
        _RUN_STORE = AgentRunStore()
    return _RUN_STORE

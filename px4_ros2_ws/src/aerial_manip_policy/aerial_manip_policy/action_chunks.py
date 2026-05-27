import json
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


@dataclass
class HighLevelAction:
    """One high-level command for existing UAV and arm bridges."""

    dt: float = 0.2
    uav_target_ned: Optional[List[float]] = None
    arm_mode: str = "hold"
    arm_joint_names: List[str] = field(default_factory=list)
    arm_joint_positions: List[float] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HighLevelAction":
        uav_target = data.get("uav_target_ned")
        if uav_target is not None:
            if not isinstance(uav_target, Sequence) or len(uav_target) != 3:
                raise ValueError("uav_target_ned must be a 3-element list")
            uav_target = [float(value) for value in uav_target]

        return cls(
            dt=max(0.0, float(data.get("dt", 0.2))),
            uav_target_ned=uav_target,
            arm_mode=str(data.get("arm_mode", "hold")),
            arm_joint_names=[str(value) for value in data.get("arm_joint_names", [])],
            arm_joint_positions=[
                float(value) for value in data.get("arm_joint_positions", [])
            ],
        )


@dataclass
class ActionChunk:
    actions: List[HighLevelAction]
    source: str = "unknown"

    @classmethod
    def from_dict(cls, data: Dict[str, Any], source: str = "unknown") -> "ActionChunk":
        raw_actions = data.get("actions", [])
        if not isinstance(raw_actions, list):
            raise ValueError("actions must be a list")
        actions = [HighLevelAction.from_dict(item) for item in raw_actions]
        return cls(actions=actions, source=str(data.get("source", source)))

    def empty(self) -> bool:
        return len(self.actions) == 0


class StaticChunkPolicy:
    """Loads deterministic high-level action chunks from JSON."""

    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self._chunks = self._load_chunks(self.path)
        self._index = 0

    def predict(self, _observation: Dict[str, Any], _timeout_sec: float) -> ActionChunk:
        if not self._chunks:
            return ActionChunk(actions=[], source=str(self.path))
        chunk = self._chunks[min(self._index, len(self._chunks) - 1)]
        self._index += 1
        return chunk

    @staticmethod
    def _load_chunks(path: Path) -> List[ActionChunk]:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            raw_chunks = data.get("chunks", [data])
        elif isinstance(data, list):
            raw_chunks = data
        else:
            raise ValueError("policy JSON must be an object or list")
        return [
            ActionChunk.from_dict(chunk, source=str(path))
            for chunk in raw_chunks
            if isinstance(chunk, dict)
        ]


class SubprocessJsonPolicy:
    """One-shot JSON stdin/stdout inference adapter for external LeRobot wrappers."""

    def __init__(self, command: Sequence[str]) -> None:
        if not command:
            raise ValueError("policy command cannot be empty")
        self.command = list(command)

    def predict(self, observation: Dict[str, Any], timeout_sec: float) -> ActionChunk:
        payload = json.dumps(observation, separators=(",", ":"))
        started = time.monotonic()
        result = subprocess.run(
            self.command,
            input=payload,
            text=True,
            capture_output=True,
            timeout=max(0.05, timeout_sec),
            check=False,
        )
        elapsed = time.monotonic() - started
        if result.returncode != 0:
            stderr = result.stderr.strip()
            raise RuntimeError(
                f"policy command failed with code {result.returncode}: {stderr}"
            )
        data = json.loads(result.stdout)
        chunk = ActionChunk.from_dict(data, source="subprocess")
        if elapsed > timeout_sec:
            raise TimeoutError(f"policy inference exceeded {timeout_sec:.3f}s")
        return chunk

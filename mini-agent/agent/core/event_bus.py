#!/usr/bin/env python3
"""
Minimal event bus and hook system for Athena.

Provides a unified envelope for events and hook points for auditing and extension.
Events flow through a simple synchronous bus; hooks can intercept/modify/add evidence.

Core concepts:
- Event envelope: standardized structure for all events
- Hook points: pre-tool, post-tool, task-start, task-finish, artifact-written
- Evidence attachment: audit evidence can be attached to events and written back to trace

Design principles:
- Minimal, synchronous, in-process only
- No external dependencies, no message brokers
- Simple registration and emission
- Integration with existing trace system
"""

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union


class EventType(Enum):
    """Core event types covering the required surface."""

    PROMPT = "prompt"  # Prompt generation/rendering
    TASK = "task"  # Task lifecycle (create, start, finish)
    TOOL = "tool"  # Tool invocation (pre/post)
    ARTIFACT = "artifact"  # Artifact written (file, output)
    REVIEW = "review"  # Review/validation events
    HOOK = "hook"  # Hook invocation meta-event


class HookPoint(Enum):
    """Standard hook points where handlers can be registered."""

    PRE_TOOL = "pre-tool"
    POST_TOOL = "post-tool"
    TASK_START = "task-start"
    TASK_FINISH = "task-finish"
    ARTIFACT_WRITTEN = "artifact-written"
    # Additional extension points
    PRE_PROMPT = "pre-prompt"
    POST_PROMPT = "post-prompt"
    PRE_REVIEW = "pre-review"
    POST_REVIEW = "post-review"


@dataclass
class EventEnvelope:
    """Unified event envelope for all Athena events."""

    event_id: str
    timestamp: str
    event_type: str
    scope: Dict[str, Any]  # e.g., {"task_id": "...", "queue_item_id": "...", "stage": "build"}
    payload: Dict[str, Any]  # Event-specific data
    metadata: Dict[str, Any] = field(default_factory=dict)  # Source, version, etc.
    evidence: List[Dict[str, Any]] = field(default_factory=list)  # Audit evidence attachments

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def create(
        cls,
        event_type: Union[str, EventType],
        scope: Dict[str, Any],
        payload: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        evidence: Optional[List[Dict[str, Any]]] = None,
    ) -> "EventEnvelope":
        """Factory method to create a new event envelope."""
        if isinstance(event_type, EventType):
            event_type = event_type.value

        return cls(
            event_id=f"evt_{uuid.uuid4().hex[:12]}",
            timestamp=datetime.now().astimezone().isoformat(timespec="seconds"),
            event_type=event_type,
            scope=scope,
            payload=payload,
            metadata=metadata or {},
            evidence=evidence or [],
        )


HookHandler = Callable[[EventEnvelope], Optional[EventEnvelope]]
"""Hook handler signature. Can return None to pass through, or a modified event."""


class EventBus:
    """
    Minimal in-process event bus with hook registration.

    Thread-safe for single-threaded use; not designed for concurrent modifications.
    """

    def __init__(self):
        self._hooks: Dict[str, List[HookHandler]] = {}
        self._event_listeners: Dict[str, List[Callable[[EventEnvelope], None]]] = {}
        self._enable_trace_integration = True

    def register_hook(self, hook_point: Union[str, HookPoint], handler: HookHandler) -> None:
        """Register a hook handler for a specific hook point."""
        point = hook_point.value if isinstance(hook_point, HookPoint) else hook_point
        if point not in self._hooks:
            self._hooks[point] = []
        self._hooks[point].append(handler)

    def register_event_listener(
        self,
        event_type: Union[str, EventType],
        listener: Callable[[EventEnvelope], None],
    ) -> None:
        """Register a listener for specific event types (fires after hooks)."""
        etype = event_type.value if isinstance(event_type, EventType) else event_type
        if etype not in self._event_listeners:
            self._event_listeners[etype] = []
        self._event_listeners[etype].append(listener)

    def emit_event(self, event: EventEnvelope) -> EventEnvelope:
        """
        Emit an event through the bus, executing hooks and listeners.

        Returns the potentially modified event (after hooks).
        """
        # 1. Execute hook-point hooks if specified in metadata
        hook_point = event.metadata.get("hook_point")
        if hook_point and hook_point in self._hooks:
            for hook in self._hooks[hook_point]:
                result = hook(event)
                if result is not None:
                    event = result

        # 2. Execute event-type listeners
        event_type = event.event_type
        if event_type in self._event_listeners:
            for listener in self._event_listeners[event_type]:
                listener(event)

        # 3. If trace integration enabled, also write to trace.json
        if self._enable_trace_integration:
            self._write_to_trace(event)

        return event

    def emit(
        self,
        event_type: Union[str, EventType],
        scope: Dict[str, Any],
        payload: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        evidence: Optional[List[Dict[str, Any]]] = None,
        hook_point: Optional[Union[str, HookPoint]] = None,
    ) -> EventEnvelope:
        """Convenience method to create and emit an event in one call."""
        if metadata is None:
            metadata = {}
        if hook_point:
            metadata["hook_point"] = (
                hook_point.value if isinstance(hook_point, HookPoint) else hook_point
            )

        event = EventEnvelope.create(
            event_type=event_type,
            scope=scope,
            payload=payload,
            metadata=metadata,
            evidence=evidence,
        )
        return self.emit_event(event)

    def _write_to_trace(self, event: EventEnvelope) -> None:
        """Write event to appropriate trace.json if scope contains task_dir."""
        task_dir = event.scope.get("task_dir")
        if not task_dir:
            return

        from pathlib import Path

        trace_path = Path(task_dir) / "trace.json"
        if not trace_path.exists():
            return

        try:
            import json

            trace = json.loads(trace_path.read_text(encoding="utf-8"))
            events = trace.setdefault("events", [])
            # Convert event to trace-compatible format
            trace_event = {
                "timestamp": event.timestamp,
                "type": f"bus:{event.event_type}",
                "data": {
                    "event_id": event.event_id,
                    "scope": event.scope,
                    "payload": event.payload,
                    "metadata": event.metadata,
                    "evidence": event.evidence,
                },
            }
            events.append(trace_event)
            trace_path.write_text(
                json.dumps(trace, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
        except Exception:
            # Silently fail; trace writing is best-effort
            pass

    def add_evidence(self, event: EventEnvelope, evidence_type: str, data: Dict[str, Any]) -> None:
        """Add audit evidence to an event (mutates the event in-place)."""
        evidence_entry = {
            "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
            "type": evidence_type,
            "data": data,
        }
        event.evidence.append(evidence_entry)


# Global singleton instance
_bus_instance: Optional[EventBus] = None


def get_bus() -> EventBus:
    """Get the global event bus instance."""
    global _bus_instance
    if _bus_instance is None:
        _bus_instance = EventBus()
    return _bus_instance


def emit_event(event: EventEnvelope) -> EventEnvelope:
    """Convenience function to emit an event via the global bus."""
    return get_bus().emit_event(event)


def emit(
    event_type: Union[str, EventType],
    scope: Dict[str, Any],
    payload: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None,
    evidence: Optional[List[Dict[str, Any]]] = None,
    hook_point: Optional[Union[str, HookPoint]] = None,
) -> EventEnvelope:
    """Convenience function to create and emit an event via the global bus."""
    return get_bus().emit(event_type, scope, payload, metadata, evidence, hook_point)


# Example hook implementations for common use cases


def create_audit_hook(audit_store_path: str) -> HookHandler:
    """Create a hook that writes audit evidence to a persistent store."""
    from pathlib import Path

    store_path = Path(audit_store_path)

    def audit_hook(event: EventEnvelope) -> None:
        # Add evidence to the event
        get_bus().add_evidence(event, "audit_trail", {"store_path": str(store_path)})
        # Also write to separate audit log
        audit_entry = {
            "timestamp": event.timestamp,
            "event_id": event.event_id,
            "event_type": event.event_type,
            "scope": event.scope,
            "summary": event.payload.get("summary", ""),
        }
        try:
            store_path.mkdir(parents=True, exist_ok=True)
            audit_file = store_path / "audit.log"
            with audit_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(audit_entry, ensure_ascii=False) + "\n")
        except Exception:
            pass
        return None  # Don't modify event

    return audit_hook


def create_validation_gate_hook(
    validation_callback: Callable[[EventEnvelope], bool],
) -> HookHandler:
    """Create a hook that acts as a validation gate; can reject events."""

    def validation_hook(event: EventEnvelope) -> Optional[EventEnvelope]:
        if not validation_callback(event):
            # Reject by returning a modified event with validation failure
            event.payload["validation_failed"] = True
            event.metadata["validation_rejected"] = True
        return event

    return validation_hook


if __name__ == "__main__":
    # Simple test/demo
    print("=== Event Bus Test ===")

    bus = EventBus()

    # Register a simple hook
    def log_hook(event: EventEnvelope) -> None:
        print(f"[HOOK] {event.metadata.get('hook_point', 'unknown')}: {event.event_type}")
        return None

    bus.register_hook(HookPoint.PRE_TOOL, log_hook)

    # Emit a test event
    event = bus.emit(
        event_type=EventType.TOOL,
        scope={"task_id": "test_task", "tool": "bash"},
        payload={"command": "ls -la", "status": "starting"},
        hook_point=HookPoint.PRE_TOOL,
    )

    print(f"Emitted event: {event.event_id}")
    print(f"  Type: {event.event_type}")
    print(f"  Scope: {event.scope}")
    print(f"  Payload: {event.payload}")
    print("\n✅ Event bus test complete")

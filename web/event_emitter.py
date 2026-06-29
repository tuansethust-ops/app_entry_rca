"""Real-time event emitter for broadcasting analysis progress via WebSocket."""
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional


@dataclass
class Event:
    """A single event emitted during analysis."""
    type: str
    data: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    job_id: str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self), default=str)


class EventEmitter:
    """Thread-safe event emitter that bridges sync skill code with async WebSocket delivery.

    Usage from sync code (skills/orchestrator):
        emitter.emit(job_id, "skill.started", {"skill": "trace-ingestion"})

    Usage from async code (WebSocket handler):
        async for event in emitter.subscribe(job_id):
            await ws.send_text(event.to_json())
    """

    def __init__(self) -> None:
        self._subscribers: Dict[str, list[asyncio.Queue]] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._logs: Dict[str, list[Event]] = {}

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def emit(self, job_id: str, event_type: str, data: Dict[str, Any] | None = None) -> None:
        """Emit an event (callable from any thread)."""
        event = Event(type=event_type, data=data or {}, job_id=job_id)

        # Store in log buffer
        if job_id not in self._logs:
            self._logs[job_id] = []
        self._logs[job_id].append(event)

        # Push to all subscribers for this job
        queues = self._subscribers.get(job_id, [])
        for q in queues:
            if self._loop and self._loop.is_running():
                self._loop.call_soon_threadsafe(q.put_nowait, event)
            else:
                try:
                    q.put_nowait(event)
                except Exception:
                    pass

    def subscribe(self, job_id: str) -> asyncio.Queue:
        """Create a subscription queue for a job. Returns an asyncio.Queue."""
        if job_id not in self._subscribers:
            self._subscribers[job_id] = []
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers[job_id].append(q)
        return q

    def unsubscribe(self, job_id: str, queue: asyncio.Queue) -> None:
        """Remove a subscription queue."""
        if job_id in self._subscribers:
            try:
                self._subscribers[job_id].remove(queue)
            except ValueError:
                pass
            if not self._subscribers[job_id]:
                del self._subscribers[job_id]

    def get_logs(self, job_id: str) -> list[Event]:
        """Get all stored events for a job."""
        return list(self._logs.get(job_id, []))

    def clear_logs(self, job_id: str) -> None:
        """Clear stored events for a job."""
        self._logs.pop(job_id, None)
        self._subscribers.pop(job_id, None)


# Global singleton
emitter = EventEmitter()

from __future__ import annotations

import re
import threading
from dataclasses import dataclass
from time import monotonic


@dataclass
class Conversation:
    topic: str
    updated_at: float


class ConversationStore:
    def __init__(self, ttl_seconds: int = 3600) -> None:
        self.ttl_seconds = ttl_seconds
        self._items: dict[tuple[str, str], Conversation] = {}
        self._lock = threading.RLock()

    def resolve(self, site_id: str, session_id: str, question: str) -> str:
        key = (site_id, session_id)
        with self._lock:
            current = self._items.get(key)
            if current and monotonic() - current.updated_at > self.ttl_seconds:
                self._items.pop(key, None)
                current = None
        follow_up = bool(re.search(
            r"\b(it|its|that|this|they|their|the document|the file|show (?:me )?the source)\b",
            question,
            flags=re.I,
        ))
        if follow_up and current:
            return f"{question} Previous topic: {current.topic}"
        return question

    def remember(self, site_id: str, session_id: str, question: str) -> None:
        with self._lock:
            self._items[(site_id, session_id)] = Conversation(question, monotonic())

    def clear(self, site_id: str, session_id: str) -> None:
        with self._lock:
            self._items.pop((site_id, session_id), None)


conversations = ConversationStore()

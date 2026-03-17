"""Conversation session management."""

from __future__ import annotations

import uuid
from datetime import datetime


class Session:
    """Tracks a single voice interaction session."""

    def __init__(self, shop_id: int) -> None:
        self.session_id = str(uuid.uuid4())[:8]
        self.shop_id = shop_id
        self.started_at = datetime.now()
        self.turn_count = 0
        # Pending disambiguation state
        self.pending_action: str | None = None
        self.pending_params: dict = {}
        self.awaiting_confirmation = False
        self.awaiting_disambiguation = False
        self.disambiguation_candidates: list[str] = []

    def next_turn(self) -> None:
        self.turn_count += 1

    def set_pending(
        self,
        action: str,
        params: dict,
        *,
        needs_confirmation: bool = False,
        needs_disambiguation: bool = False,
        candidates: list[str] | None = None,
    ) -> None:
        self.pending_action = action
        self.pending_params = params
        self.awaiting_confirmation = needs_confirmation
        self.awaiting_disambiguation = needs_disambiguation
        self.disambiguation_candidates = candidates or []

    def clear_pending(self) -> None:
        self.pending_action = None
        self.pending_params = {}
        self.awaiting_confirmation = False
        self.awaiting_disambiguation = False
        self.disambiguation_candidates = []

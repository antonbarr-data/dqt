from __future__ import annotations

from uuid import UUID

from dqt.subscriptions.models import Subscription


class SubscriptionStore:
    def __init__(self) -> None:
        self._subs: dict[UUID, Subscription] = {}

    def save(self, sub: Subscription) -> None:
        self._subs[sub.id] = sub

    def get(self, sub_id: UUID) -> Subscription | None:
        return self._subs.get(sub_id)

    def list_for_user(self, user_id: str) -> list[Subscription]:
        return [s for s in self._subs.values() if s.user_id == user_id]

    def list_for_metric(self, metric_fqn: str) -> list[Subscription]:
        return [s for s in self._subs.values() if metric_fqn in s.metric_fqns]

    def update(self, sub: Subscription) -> None:
        self._subs[sub.id] = sub

    def delete(self, sub_id: UUID) -> bool:
        if sub_id in self._subs:
            del self._subs[sub_id]
            return True
        return False

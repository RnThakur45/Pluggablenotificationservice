"""Pluggable notifications via composition + polymorphism.

NotificationService HAS-A list of Notifier objects (composition) and talks to
them only through the Notifier interface (polymorphism). Adding a new channel
means writing a new Notifier subclass; the service never changes.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Iterable


@dataclass(frozen=True)
class Alert:
    title: str
    body: str


class Notifier(ABC):
    """The one interface the service depends on."""

    @abstractmethod
    def send(self, alert: Alert) -> None: ...


class EmailNotifier(Notifier):
    def __init__(self, to: str, transport: Callable[[str, str, str], None]):
        self._to = to
        self._transport = transport  # (to, subject, body)

    def send(self, alert: Alert) -> None:
        self._transport(self._to, alert.title, alert.body)


class SlackNotifier(Notifier):
    def __init__(self, channel: str, transport: Callable[[str, str], None]):
        self._channel = channel
        self._transport = transport  # (channel, text)

    def send(self, alert: Alert) -> None:
        self._transport(self._channel, f"*{alert.title}*\n{alert.body}")


class SmsNotifier(Notifier):
    MAX_LEN = 160

    def __init__(self, phone: str, transport: Callable[[str, str], None]):
        self._phone = phone
        self._transport = transport  # (phone, text)

    def send(self, alert: Alert) -> None:
        text = f"{alert.title}: {alert.body}"
        if len(text) > self.MAX_LEN:
            text = text[: self.MAX_LEN - 1] + "…"
        self._transport(self._phone, text)


@dataclass(frozen=True)
class Failure:
    notifier: Notifier
    error: Exception


class NotificationService:
    def __init__(self, notifiers: Iterable[Notifier] = ()):
        self._notifiers = list(notifiers)

    def add(self, notifier: Notifier) -> None:
        self._notifiers.append(notifier)

    def notify(self, alert: Alert) -> list[Failure]:
        """Send to every channel; one failing channel doesn't block the rest."""
        failures: list[Failure] = []
        for notifier in self._notifiers:
            try:
                notifier.send(alert)
            except Exception as exc:  # isolate channel failures
                failures.append(Failure(notifier, exc))
        return failures

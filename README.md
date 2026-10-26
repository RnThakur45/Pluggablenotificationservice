# Pluggable NotificationService

A small Python example of **composition** and **polymorphism**: a `NotificationService` that sends alerts through any combination of `EmailNotifier`, `SlackNotifier`, and `SmsNotifier`, tested with a `SpyNotifier`.

No third-party dependencies. Python 3.9+.

## Design

```
NotificationService  ──has-a──▶  [Notifier, Notifier, ...]
                                     ▲
                      ┌──────────────┼──────────────┐
                EmailNotifier  SlackNotifier  SmsNotifier
```

- **Composition:** `NotificationService` holds a list of `Notifier` objects. It does not inherit from them.
- **Polymorphism:** the service only calls `notifier.send(alert)` on the abstract `Notifier` interface. Each subclass decides how to deliver.
- **Open for extension:** a new channel is one new `Notifier` subclass. The service never changes.
- **Injected transports:** each concrete notifier takes a destination and a transport callable (SMTP client, Slack webhook poster, SMS gateway, etc.), so nothing touches the network in tests.
- **Failure isolation:** `notify()` tries every channel. If one raises, the rest still send, and the failures are returned.

## Files

| File | Purpose |
|------|---------|
| `notification.py` | `Alert`, `Notifier` (ABC), the three notifiers, `NotificationService`, `Failure` |
| `test_notification.py` | Unit tests, including the `SpyNotifier` test double |

## Usage

```python
from notification import (
    Alert, EmailNotifier, SlackNotifier, SmsNotifier, NotificationService,
)

def send_email(to, subject, body):   # wrap smtplib, SendGrid, etc.
    ...

def post_slack(channel, text):       # wrap a webhook call
    ...

def send_sms(phone, text):           # wrap Twilio, etc.
    ...

service = NotificationService([
    EmailNotifier("oncall@example.com", send_email),
    SlackNotifier("#ops", post_slack),
])
service.add(SmsNotifier("+15551234567", send_sms))  # plug in another later

failures = service.notify(Alert("Disk full", "/var is at 99%"))
for f in failures:
    print(f"{type(f.notifier).__name__} failed: {f.error}")
```

### Channel behavior

| Notifier | Destination | Formatting |
|----------|-------------|------------|
| `EmailNotifier` | email address | alert title becomes the subject, body is the body |
| `SlackNotifier` | channel name | `*title*` (bold) followed by the body on a new line |
| `SmsNotifier` | phone number | `title: body`, truncated to 160 characters with `…` |

### Adding a new channel

```python
class PagerDutyNotifier(Notifier):
    def __init__(self, service_key, transport):
        self._key = service_key
        self._transport = transport

    def send(self, alert: Alert) -> None:
        self._transport(self._key, alert.title, alert.body)

service.add(PagerDutyNotifier("abc123", trigger_incident))
```

## Running the tests

```bash
python3 -m unittest -v
```

## Testing approach

`SpyNotifier` is a test double that implements `Notifier` and records every alert it receives:

```python
class SpyNotifier(Notifier):
    def __init__(self):
        self.sent = []

    def send(self, alert):
        self.sent.append(alert)
```

Because the service depends only on the `Notifier` interface, tests can swap in the spy and assert on `spy.sent` without mocking frameworks or network calls.

Covered cases:

- an alert reaches the spy
- an alert fans out to every notifier
- `add()` plugs in a notifier after construction
- a failing channel is reported and does not block the others
- an empty service is a no-op
- each concrete notifier formats its message correctly (using fake transports)
- `Notifier` cannot be instantiated directly

## Possible extensions

- Async sending (`asyncio.gather`) for slow channels
- Retries with backoff inside a wrapper `Notifier` (a decorator that composes another notifier)
- Per-alert severity routing (e.g. SMS only for critical alerts)

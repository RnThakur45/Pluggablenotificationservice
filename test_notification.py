import unittest

from notification import (
    Alert, EmailNotifier, Failure, NotificationService, Notifier,
    SlackNotifier, SmsNotifier,
)


class SpyNotifier(Notifier):
    """Test double: records what it was asked to send."""

    def __init__(self):
        self.sent: list[Alert] = []

    def send(self, alert: Alert) -> None:
        self.sent.append(alert)


class BrokenNotifier(Notifier):
    def send(self, alert: Alert) -> None:
        raise ConnectionError("channel down")


ALERT = Alert("Disk full", "/var is at 99%")


class NotificationServiceTests(unittest.TestCase):
    def test_delivers_alert_to_spy(self):
        spy = SpyNotifier()
        failures = NotificationService([spy]).notify(ALERT)
        self.assertEqual(spy.sent, [ALERT])
        self.assertEqual(failures, [])

    def test_fans_out_to_every_notifier(self):
        a, b = SpyNotifier(), SpyNotifier()
        NotificationService([a, b]).notify(ALERT)
        self.assertEqual(a.sent, [ALERT])
        self.assertEqual(b.sent, [ALERT])

    def test_add_plugs_in_a_notifier_later(self):
        svc, spy = NotificationService(), SpyNotifier()
        svc.add(spy)
        svc.notify(ALERT)
        self.assertEqual(spy.sent, [ALERT])

    def test_failing_channel_is_reported_and_does_not_block_others(self):
        broken, spy = BrokenNotifier(), SpyNotifier()
        failures = NotificationService([broken, spy]).notify(ALERT)
        self.assertEqual(spy.sent, [ALERT])
        self.assertEqual(len(failures), 1)
        self.assertIs(failures[0].notifier, broken)
        self.assertIsInstance(failures[0].error, ConnectionError)

    def test_no_notifiers_is_a_noop(self):
        self.assertEqual(NotificationService().notify(ALERT), [])


class ConcreteNotifierTests(unittest.TestCase):
    def test_email_maps_title_to_subject(self):
        calls = []
        EmailNotifier("a@x.com", lambda *a: calls.append(a)).send(ALERT)
        self.assertEqual(calls, [("a@x.com", "Disk full", "/var is at 99%")])

    def test_slack_formats_title_bold(self):
        calls = []
        SlackNotifier("#ops", lambda *a: calls.append(a)).send(ALERT)
        self.assertEqual(calls, [("#ops", "*Disk full*\n/var is at 99%")])

    def test_sms_truncates_to_160_chars(self):
        calls = []
        SmsNotifier("+15551234567", lambda *a: calls.append(a)).send(
            Alert("Big", "x" * 500)
        )
        phone, text = calls[0]
        self.assertEqual(phone, "+15551234567")
        self.assertEqual(len(text), 160)
        self.assertTrue(text.endswith("…"))

    def test_notifier_is_abstract(self):
        with self.assertRaises(TypeError):
            Notifier()


if __name__ == "__main__":
    unittest.main()

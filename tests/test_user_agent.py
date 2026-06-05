"""Tests for utils.user_agent."""
import unittest
from utils.user_agent import random_ua, UserAgentGenerator


class TestRandomUA(unittest.TestCase):
    def test_returns_non_empty_string(self):
        ua = random_ua()
        self.assertIsInstance(ua, str)
        self.assertGreater(len(ua), 50)

    def test_returns_different_on_successive_calls(self):
        uas = set()
        for _ in range(100):
            uas.add(random_ua()[:40])
        self.assertGreater(len(uas), 1, "Expected >1 unique UA in 100 calls")

    def test_output_looks_like_browser_ua(self):
        ua = random_ua()
        self.assertTrue(
            any(b in ua for b in ("Chrome/", "Firefox/", "Safari/", "Edg/", "OPR/", "QQBrowser/")),
            f"UA should contain a browser identifier, got: {ua}",
        )


class TestUserAgentGenerator(unittest.TestCase):
    def setUp(self):
        self.gen = UserAgentGenerator()

    def test_desktop_ua_contains_platform(self):
        ua = self.gen.get_realistic_user_agent(mobile_mode=False)
        self.assertTrue(
            any(p in ua for p in ("Windows NT", "Macintosh", "Linux")),
            f"Desktop UA should contain a platform, got: {ua}",
        )

    def test_mobile_ua_contains_mobile_marker(self):
        ua = self.gen.get_realistic_user_agent(mobile_mode=True)
        self.assertIn("Mobile", ua)

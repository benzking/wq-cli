"""Tests for cli.subscribe — subscribe, unsubscribe, subscriptions, poll."""
import io
import json
import sys
import unittest
from unittest.mock import patch
from cli.subscribe import cmd_subscribe, cmd_unsubscribe, cmd_subscriptions, cmd_poll


class TestSubscribe(unittest.TestCase):
    @patch('cli.subscribe._req')
    def test_subscribe_success(self, mock_req):
        mock_req.return_value = (200, {"success": True, "message": "订阅成功"})
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            with self.assertRaises(SystemExit):
                cmd_subscribe("abc", "TestAccount")
        finally:
            sys.stdout = old_stdout
        data = json.loads(captured.getvalue())
        self.assertTrue(data["ok"])
        self.assertEqual(data["data"]["fakeid"], "abc")

    @patch('cli.subscribe._req')
    def test_subscribe_http_failure(self, mock_req):
        mock_req.return_value = (500, {"error": "server error"})
        with self.assertRaises(SystemExit) as cm:
            cmd_subscribe("abc", "")
        self.assertEqual(cm.exception.code, 1)


class TestUnsubscribe(unittest.TestCase):
    @patch('cli.subscribe._req')
    def test_unsubscribe_success(self, mock_req):
        mock_req.return_value = (200, {"success": True, "message": "已取消订阅"})
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            with self.assertRaises(SystemExit):
                cmd_unsubscribe("abc")
        finally:
            sys.stdout = old_stdout
        data = json.loads(captured.getvalue())
        self.assertTrue(data["ok"])


class TestSubscriptions(unittest.TestCase):
    @patch('cli.subscribe._req')
    def test_subscriptions_json(self, mock_req):
        mock_req.return_value = (200, {"success": True, "data": [
            {"fakeid": "abc", "nickname": "Test", "article_count": 10, "rss_url": "http://..."}
        ]})
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            with self.assertRaises(SystemExit):
                cmd_subscriptions(fmt="json")
        finally:
            sys.stdout = old_stdout
        data = json.loads(captured.getvalue())
        self.assertEqual(data["data"][0]["nickname"], "Test")


class TestPoll(unittest.TestCase):
    @patch('cli.subscribe._req')
    def test_poll_success(self, mock_req):
        mock_req.return_value = (200, {"success": True, "data": {"message": "轮询完成"}})
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            with self.assertRaises(SystemExit):
                cmd_poll()
        finally:
            sys.stdout = old_stdout
        data = json.loads(captured.getvalue())
        self.assertTrue(data["ok"])

"""Tests for cli.health — check, status."""
import io
import json
import sys
import unittest
from unittest.mock import patch
from cli.health import cmd_check, cmd_status


class TestCheck(unittest.TestCase):
    @patch('cli.health._req')
    def test_check_healthy_authenticated(self, mock_req):
        mock_req.side_effect = [
            (200, {"status": "healthy"}),
            (200, {"authenticated": True, "isExpired": False, "status": "正常", "nickname": "test", "fakeid": "abc", "effective_route": "L1 → L3"}),
        ]
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            with self.assertRaises(SystemExit):
                cmd_check(auto_recover=False)
        finally:
            sys.stdout = old_stdout
        data = json.loads(captured.getvalue())
        self.assertTrue(data["ok"])
        self.assertTrue(data["data"]["service_healthy"])
        self.assertTrue(data["data"]["authenticated"])

    @patch('cli.health._req')
    def test_check_service_down(self, mock_req):
        mock_req.side_effect = [
            (0, {"error": "connection refused"}),
            (0, {"error": "connection refused"}),
        ]
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            with self.assertRaises(SystemExit):
                cmd_check(auto_recover=False)
        finally:
            sys.stdout = old_stdout
        data = json.loads(captured.getvalue())
        self.assertTrue(data["ok"])
        self.assertFalse(data["data"]["service_healthy"])

    @patch('cli.health._req')
    def test_check_not_authenticated(self, mock_req):
        mock_req.side_effect = [
            (200, {"status": "healthy"}),
            (200, {"authenticated": False, "isExpired": True, "status": "未登录", "nickname": "", "fakeid": ""}),
        ]
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            with self.assertRaises(SystemExit):
                cmd_check(auto_recover=False)
        finally:
            sys.stdout = old_stdout
        data = json.loads(captured.getvalue())
        self.assertTrue(data["ok"])
        self.assertFalse(data["data"]["ok"])


class TestStatus(unittest.TestCase):
    @patch('cli.health._req')
    def test_status_success(self, mock_req):
        mock_req.return_value = (200, {"authenticated": True, "isExpired": False, "status": "正常"})
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            with self.assertRaises(SystemExit):
                cmd_status()
        finally:
            sys.stdout = old_stdout
        data = json.loads(captured.getvalue())
        self.assertTrue(data["ok"])
        self.assertTrue(data["data"]["authenticated"])

    @patch('cli.health._req')
    def test_status_failure(self, mock_req):
        mock_req.return_value = (500, {"error": "internal error"})
        with self.assertRaises(SystemExit) as cm:
            cmd_status()
        self.assertEqual(cm.exception.code, 1)

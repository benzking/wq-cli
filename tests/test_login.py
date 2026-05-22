"""Tests for cli.login."""
import io
import sys
import unittest
from unittest.mock import patch
from cli.login import cmd_login


class TestLogin(unittest.TestCase):
    def test_login_output_contains_url(self):
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            with self.assertRaises(SystemExit):
                cmd_login()
        finally:
            sys.stdout = old_stdout
        output = captured.getvalue()
        self.assertIn("login.html", output)

    @patch('cli.login._req')
    def test_login_shows_expired_warning(self, mock_req):
        mock_req.return_value = (200, {"authenticated": True, "isExpired": True, "status": "已过期"})
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            with self.assertRaises(SystemExit):
                cmd_login()
        finally:
            sys.stdout = old_stdout
        output = captured.getvalue()
        self.assertIn("EXPIRED", output.upper())

    @patch('cli.login._req')
    def test_login_shows_not_logged_in(self, mock_req):
        mock_req.return_value = (200, {"authenticated": False, "isExpired": False, "status": "未登录"})
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            with self.assertRaises(SystemExit):
                cmd_login()
        finally:
            sys.stdout = old_stdout
        output = captured.getvalue()
        self.assertIn("NOT LOGGED IN", output.upper())

"""Tests for cli.search — search, info."""
import io
import json
import sys
import unittest
from unittest.mock import patch
from cli.search import cmd_search, cmd_info


class TestSearch(unittest.TestCase):
    @patch('cli.search._req')
    def test_search_returns_list(self, mock_req):
        mock_req.return_value = (200, {
            "success": True,
            "data": {"list": [{"fakeid": "abc", "nickname": "TestAccount", "alias": "test"}]}
        })
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            with self.assertRaises(SystemExit):
                cmd_search("test", fmt="json")
        finally:
            sys.stdout = old_stdout
        data = json.loads(captured.getvalue())
        self.assertTrue(data["ok"])
        self.assertEqual(data["data"][0]["fakeid"], "abc")

    @patch('cli.search._req')
    def test_search_no_results(self, mock_req):
        mock_req.return_value = (200, {"success": True, "data": {"list": []}})
        with self.assertRaises(SystemExit) as cm:
            cmd_search("nobody", fmt="json")
        self.assertEqual(cm.exception.code, 1)

    @patch('cli.search._req')
    def test_search_api_failure(self, mock_req):
        mock_req.return_value = (500, {"error": "internal error"})
        with self.assertRaises(SystemExit) as cm:
            cmd_search("test", fmt="json")
        self.assertEqual(cm.exception.code, 1)

    @patch('cli.search._req')
    def test_search_table_format(self, mock_req):
        mock_req.return_value = (200, {
            "success": True,
            "data": {"list": [{"fakeid": "abc", "nickname": "Test", "alias": "t", "round_head_img": "http://img"}]
            }
        })
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            with self.assertRaises(SystemExit):
                cmd_search("test", fmt="table")
        finally:
            sys.stdout = old_stdout
        output = captured.getvalue()
        self.assertIn("Test", output)


class TestInfo(unittest.TestCase):
    @patch('cli.search._req')
    def test_info_success(self, mock_req):
        mock_req.return_value = (200, {
            "data": {"identity_name": "TestCompany", "is_verify": 2, "original_article_count": 15234}
        })
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            with self.assertRaises(SystemExit):
                cmd_info("abc")
        finally:
            sys.stdout = old_stdout
        data = json.loads(captured.getvalue())
        self.assertTrue(data["ok"])
        self.assertEqual(data["data"]["identity_name"], "TestCompany")

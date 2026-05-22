"""Tests for cli.articles — query cached articles."""
import io
import json
import sqlite3
import sys
import unittest
from unittest.mock import patch
from cli.articles import cmd_articles


class TestArticlesDB(unittest.TestCase):
    @patch('cli.articles._db_conn')
    def test_articles_returns_list(self, mock_db):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("CREATE TABLE articles (id INTEGER PRIMARY KEY, fakeid TEXT, title TEXT, link TEXT, author TEXT, digest TEXT, publish_time INTEGER, fetched_at INTEGER)")
        conn.execute("CREATE TABLE subscriptions (fakeid TEXT PRIMARY KEY, nickname TEXT)")
        conn.execute("INSERT INTO subscriptions VALUES ('abc', 'TestAccount')")
        conn.execute("INSERT INTO articles VALUES (1, 'abc', 'Test', 'http://...', 'A', 'D', 1700000000, 1700000000)")
        mock_db.return_value = conn
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            with self.assertRaises(SystemExit):
                cmd_articles(fakeid=None, hours=None, keyword=None, limit=20, fmt="json")
        finally:
            sys.stdout = old_stdout
        data = json.loads(captured.getvalue())
        self.assertTrue(data["ok"])
        self.assertEqual(len(data["data"]), 1)
        self.assertEqual(data["data"][0]["title"], "Test")

    @patch('cli.articles._db_conn')
    @patch('cli.articles._req')
    def test_articles_api_fallback(self, mock_req, mock_db):
        mock_db.return_value = None
        mock_req.return_value = (200, {"success": True, "data": [
            {"id": 1, "title": "API Article", "link": "http://...", "fakeid": "abc",
             "nickname": "Test", "digest": "D", "publish_time": 1700000000, "author": "A"}
        ]})
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            with self.assertRaises(SystemExit):
                cmd_articles(fakeid="abc", hours=None, keyword=None, limit=20, fmt="json")
        finally:
            sys.stdout = old_stdout
        data = json.loads(captured.getvalue())
        self.assertTrue(data["ok"])
        self.assertEqual(data["data"][0]["title"], "API Article")

    @patch('cli.articles._db_conn')
    def test_articles_table_format(self, mock_db):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("CREATE TABLE articles (id INTEGER PRIMARY KEY, fakeid TEXT, title TEXT, link TEXT, author TEXT, digest TEXT, publish_time INTEGER, fetched_at INTEGER)")
        conn.execute("CREATE TABLE subscriptions (fakeid TEXT PRIMARY KEY, nickname TEXT)")
        conn.execute("INSERT INTO subscriptions VALUES ('abc', 'TestAccount')")
        conn.execute("INSERT INTO articles VALUES (1, 'abc', 'Test', 'http://...', 'A', 'D', 1700000000, 1700000000)")
        mock_db.return_value = conn
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            with self.assertRaises(SystemExit):
                cmd_articles(fakeid=None, hours=None, keyword=None, limit=20, fmt="table")
        finally:
            sys.stdout = old_stdout
        output = captured.getvalue()
        self.assertIn("Test", output)
        self.assertIn("|", output)

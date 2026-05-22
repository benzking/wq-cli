"""Tests for cli.push — push-report, md-push."""
import io
import json
import sqlite3
import sys
import time
import unittest
from unittest.mock import patch
from cli.push import cmd_push_report, cmd_md_push


class TestPushReport(unittest.TestCase):
    @patch('cli.push._db_conn')
    @patch('cli.push._req')
    def test_push_report_with_articles(self, mock_req, mock_db):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("CREATE TABLE articles (id INTEGER PRIMARY KEY, fakeid TEXT, title TEXT, link TEXT, author TEXT, digest TEXT, publish_time INTEGER, fetched_at INTEGER)")
        conn.execute("CREATE TABLE subscriptions (fakeid TEXT PRIMARY KEY, nickname TEXT)")
        conn.execute("INSERT INTO subscriptions VALUES ('abc', 'Test')")
        conn.execute("INSERT INTO articles VALUES (1, 'abc', 'T', 'http://...', 'A', 'D', ?, ?)",
                     (int(time.time()) - 3600, int(time.time()) - 3600))
        mock_db.return_value = conn
        mock_req.return_value = (200, {"authenticated": True, "isExpired": False, "status": "正常"})
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            with self.assertRaises(SystemExit):
                cmd_push_report(hours=24)
        finally:
            sys.stdout = old_stdout
        data = json.loads(captured.getvalue())
        self.assertTrue(data["ok"])
        self.assertEqual(data["data"]["article_count"], 1)
        self.assertEqual(data["data"]["period_hours"], 24)

    @patch('cli.push._db_conn')
    def test_push_report_no_db(self, mock_db):
        mock_db.return_value = None
        with self.assertRaises(SystemExit) as cm:
            cmd_push_report(hours=24)
        self.assertEqual(cm.exception.code, 1)


class TestMDPush(unittest.TestCase):
    @patch('cli.push._db_conn')
    @patch('cli.push._req')
    def test_md_push_no_articles(self, mock_req, mock_db):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("CREATE TABLE articles (id INTEGER PRIMARY KEY, fakeid TEXT, title TEXT, link TEXT, author TEXT, digest TEXT, publish_time INTEGER, fetched_at INTEGER)")
        conn.execute("CREATE TABLE subscriptions (fakeid TEXT PRIMARY KEY, nickname TEXT)")
        mock_db.return_value = conn
        mock_req.return_value = (200, {"authenticated": True, "isExpired": False, "status": "正常"})
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            with self.assertRaises(SystemExit):
                cmd_md_push(hours=24)
        finally:
            sys.stdout = old_stdout
        output = captured.getvalue()
        self.assertIn("wq", output)

    @patch('cli.push._req')
    def test_md_push_with_articles_output(self, mock_req):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("CREATE TABLE articles (id INTEGER PRIMARY KEY, fakeid TEXT, title TEXT, link TEXT, author TEXT, digest TEXT, publish_time INTEGER, fetched_at INTEGER)")
        conn.execute("CREATE TABLE subscriptions (fakeid TEXT PRIMARY KEY, nickname TEXT)")
        conn.execute("INSERT INTO subscriptions VALUES ('abc', 'TestAccount')")
        conn.execute("INSERT INTO articles VALUES (1, 'abc', 'My Article', 'http://link', 'A', 'Digest here', ?, ?)",
                     (int(time.time()) - 3600, int(time.time()) - 3600))
        with patch('cli.push._db_conn', return_value=conn):
            mock_req.return_value = (200, {"authenticated": True, "isExpired": False, "status": "OK"})
            captured = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = captured
            try:
                with self.assertRaises(SystemExit):
                    cmd_md_push(hours=24)
            finally:
                sys.stdout = old_stdout
            output = captured.getvalue()
            self.assertIn("My Article", output)
            self.assertIn("TestAccount", output)

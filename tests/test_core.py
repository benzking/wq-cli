"""Tests for cli.core — _ok, _fail, _db_conn, _download_images, _validate_image_bytes."""
import io
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from cli.core import _ok, _fail, _validate_image_bytes


class TestOkFail(unittest.TestCase):
    def test_ok_outputs_json_and_exits_0(self):
        with self.assertRaises(SystemExit) as cm:
            _ok({"msg": "hello"})
        self.assertEqual(cm.exception.code, 0)

    def test_ok_outputs_formatted_json(self):
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            with self.assertRaises(SystemExit):
                _ok({"key": "value"})
        finally:
            sys.stdout = old_stdout
        output = captured.getvalue()
        parsed = json.loads(output)
        self.assertTrue(parsed["ok"])
        self.assertEqual(parsed["data"], {"key": "value"})

    def test_fail_outputs_json_and_exits_1(self):
        with self.assertRaises(SystemExit) as cm:
            _fail("something broke")
        self.assertEqual(cm.exception.code, 1)

    def test_fail_custom_exit_code(self):
        with self.assertRaises(SystemExit) as cm:
            _fail("auth expired", exit_code=2)
        self.assertEqual(cm.exception.code, 2)

    def test_fail_includes_error_message(self):
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            with self.assertRaises(SystemExit):
                _fail("connection refused")
        finally:
            sys.stdout = old_stdout
        output = captured.getvalue()
        parsed = json.loads(output)
        self.assertFalse(parsed["ok"])
        self.assertEqual(parsed["error"], "connection refused")


class TestValidateImageBytes(unittest.TestCase):
    def test_jpeg_magic_valid(self):
        self.assertTrue(_validate_image_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF"))

    def test_png_magic_valid(self):
        self.assertTrue(_validate_image_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"))

    def test_gif_magic_valid(self):
        self.assertTrue(_validate_image_bytes(b"GIF89a\x01\x00\x01\x00"))

    def test_webp_magic_valid(self):
        self.assertTrue(_validate_image_bytes(b"RIFF\x00\x00\x00\x00WEBP"))

    def test_svg_magic_valid(self):
        self.assertTrue(_validate_image_bytes(b"<?xml version=\"1.0\"?>"))
        self.assertTrue(_validate_image_bytes(b"<svg xmlns=\"http://www.w3.org/2000/svg\">"))

    def test_non_image_bytes_rejected(self):
        self.assertFalse(_validate_image_bytes(b"#!/bin/bash\necho pwned"))
        self.assertFalse(_validate_image_bytes(b"\x00\x00\x00\x00\x00\x00"))
        self.assertFalse(_validate_image_bytes(b"plain text not an image"))


class TestDBConn(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test.db")
        conn = sqlite3.connect(self.db_path)
        conn.execute("CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)")
        conn.execute("INSERT OR REPLACE INTO config VALUES ('test', 'hello')")
        conn.commit()
        conn.close()

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.chmod(self.db_path, 0o644)
            os.unlink(self.db_path)
        os.rmdir(self.tmpdir)

    def test_level2_readonly_when_dir_not_writable(self):
        """When dir has no write permission, fallback to readonly mode works."""
        from cli.core import _db_conn
        import cli.core as core_mod

        os.chmod(self.db_path, 0o444)
        old_path = core_mod.DB_PATH
        core_mod.DB_PATH = self.db_path
        try:
            conn = _db_conn()
            self.assertIsNotNone(conn)
            row = conn.execute("SELECT value FROM config WHERE key='test'").fetchone()
            self.assertEqual(row[0], 'hello')
            conn.close()
        finally:
            core_mod.DB_PATH = old_path


class TestASCIIFallback(unittest.TestCase):
    def test_ascii_table_renders_basic(self):
        from cli.core import _ascii_table
        rows = [["Alice", "123"], ["Bob", "456"]]
        output = _ascii_table(rows, ["Name", "ID"])
        self.assertIn("Name", output)
        self.assertIn("Alice", output)
        self.assertIn("Bob", output)
        self.assertIn("|", output)

    def test_ascii_table_empty(self):
        from cli.core import _ascii_table
        output = _ascii_table([], ["A", "B"])
        self.assertEqual(output, "(empty)")

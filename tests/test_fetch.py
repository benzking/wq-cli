"""Tests for cli.fetch — fetch article with json/md/mhtml output."""
import io
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch
from cli.fetch import cmd_fetch, _WECHAT_BASE_CSS


class TestBaseCSS(unittest.TestCase):
    def test_base_css_is_non_empty(self):
        self.assertIn("font-family", _WECHAT_BASE_CSS)
        self.assertIn("max-width", _WECHAT_BASE_CSS)
        self.assertIn("line-height", _WECHAT_BASE_CSS)


class TestFetchJSON(unittest.TestCase):
    @patch('cli.fetch._req')
    def test_fetch_json_success(self, mock_req):
        mock_req.return_value = (200, {
            "success": True,
            "data": {
                "title": "Test Article",
                "content": "<div>Hello</div>",
                "plain_content": "Hello",
                "author": "作者",
                "publish_time": 1700000000,
                "images": []
            }
        })
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            with self.assertRaises(SystemExit):
                cmd_fetch("https://mp.weixin.qq.com/s/test", fmt="json", outdir=".")
        finally:
            sys.stdout = old_stdout
        data = json.loads(captured.getvalue())
        self.assertTrue(data["ok"])
        self.assertEqual(data["data"]["title"], "Test Article")

    @patch('cli.fetch._req')
    def test_fetch_json_failure(self, mock_req):
        mock_req.return_value = (200, {"success": False, "error": "Login expired"})
        with self.assertRaises(SystemExit) as cm:
            cmd_fetch("https://mp.weixin.qq.com/s/test", fmt="json", outdir=".")
        self.assertEqual(cm.exception.code, 1)


class TestFetchMD(unittest.TestCase):
    @patch('cli.fetch._download_images')
    @patch('cli.fetch._req')
    def test_fetch_md_success(self, mock_req, mock_dl):
        mock_req.return_value = (200, {
            "success": True,
            "data": {
                "title": "Test MD Article",
                "content": "<div><p>Hello world</p></div>",
                "plain_content": "Hello world",
                "author": "Author",
                "publish_time": 1700000000,
                "images": []
            }
        })
        mock_dl.return_value = {}
        tmpdir = tempfile.mkdtemp()
        try:
            captured = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = captured
            try:
                with self.assertRaises(SystemExit):
                    cmd_fetch("https://mp.weixin.qq.com/s/test", fmt="md", outdir=tmpdir)
            finally:
                sys.stdout = old_stdout
            data = json.loads(captured.getvalue())
            self.assertTrue(data["ok"])
            self.assertIn("md_path", data["data"])
            self.assertTrue(os.path.exists(data["data"]["md_path"]))
        finally:
            pass


class TestFetchMHTML(unittest.TestCase):
    @patch('cli.fetch._download_images')
    @patch('cli.fetch._req')
    def test_fetch_mhtml_success(self, mock_req, mock_dl):
        mock_req.return_value = (200, {
            "success": True,
            "data": {
                "title": "Test MHTML Article",
                "content": "<div><p>Hello</p><img src='https://mmbiz.qpic.cn/b.jpg'></div>",
                "plain_content": "Hello",
                "author": "",
                "publish_time": 1700000000,
                "images": ["https://mmbiz.qpic.cn/b.jpg"]
            }
        })
        # Create a tiny valid JPEG for testing
        img_dir = os.path.join(tempfile.mkdtemp(), "img")
        os.makedirs(img_dir, exist_ok=True)
        jpg_path = os.path.join(img_dir, "test.jpg")
        with open(jpg_path, 'wb') as f:
            f.write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\x09\x09\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\x1c9\x82\x0b\xff\xd9')
        mock_dl.return_value = {"https://mmbiz.qpic.cn/b.jpg": jpg_path}
        tmpdir = tempfile.mkdtemp()
        try:
            captured = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = captured
            try:
                with self.assertRaises(SystemExit):
                    cmd_fetch("https://mp.weixin.qq.com/s/test", fmt="mhtml", outdir=tmpdir)
            finally:
                sys.stdout = old_stdout
            data = json.loads(captured.getvalue())
            self.assertTrue(data["ok"])
            self.assertIn("mhtml_path", data["data"])
            self.assertTrue(os.path.exists(data["data"]["mhtml_path"]))
        finally:
            pass

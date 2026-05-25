"""Tests for cli.login and routes/login.py."""
import io
import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from cli.login import cmd_login
from fastapi.testclient import TestClient


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


class TestGetQrcode(unittest.TestCase):
    """测试 /api/login/getqrcode 端点——二维码获取与保存的容错性。"""

    def setUp(self):
        os.environ.setdefault("WECHAT_TOKEN", "test-token")
        os.environ.setdefault("WECHAT_COOKIE", "test-cookie")
        os.environ.setdefault("WECHAT_FAKEID", "test-fakeid")
        from app import app
        self.client = TestClient(app)

    def test_qrcode_survives_permission_error(self):
        """当二维码保存到磁盘因权限不足失败时，端点仍返回 200 和图片内容。"""
        jpeg_content = (
            b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
            b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\x09\x09"
            b"\xff\xd9"
        )

        with patch("routes.login.proxy_wx_request") as mock_proxy:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "image/jpeg"}
            mock_response.content = jpeg_content
            mock_proxy.return_value = mock_response

            with patch("builtins.open") as mock_open:
                mock_open.side_effect = PermissionError(
                    "[Errno 13] Permission denied: 'static/qrcodes/login_qrcode.jpg'"
                )

                response = self.client.get("/api/login/getqrcode")

                self.assertEqual(response.status_code, 200,
                    f"权限错误不应导致 500，实际 status={response.status_code}")
                self.assertEqual(response.content, jpeg_content,
                    "即使保存失败，二维码图片内容仍应正确返回")
                self.assertIn("image/jpeg", response.headers.get("content-type", ""),
                    "响应 Content-Type 应为 image/jpeg")

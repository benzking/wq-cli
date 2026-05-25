"""Tests for admin.html homepage navigation links."""
import unittest
from fastapi.testclient import TestClient


class TestAdminPageNavigation(unittest.TestCase):
    """验证主页面 admin.html 包含所有功能模块的导航链接。"""

    def setUp(self):
        from app import app
        self.client = TestClient(app)

    def test_homepage_serves_admin_html(self):
        """首页 (/) 返回 admin.html，状态码 200。"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers.get("content-type", ""))

    def test_admin_page_has_browse_link(self):
        """主页面应包含「文章在线展示」(browse) 导航链接。"""
        response = self.client.get("/")
        html = response.text
        self.assertIn("/browse.html", html,
            "主页面缺少文章在线展示 (browse.html) 链接")

    def test_admin_page_has_logs_link(self):
        """主页面应包含「全平台日志」(logs) 导航链接。"""
        response = self.client.get("/")
        html = response.text
        self.assertIn("/logs.html", html,
            "主页面缺少全平台日志 (logs.html) 链接")

    def test_admin_page_has_ingestion_link(self):
        """主页面应包含「入库管理」(ingestion) 导航链接。"""
        response = self.client.get("/")
        html = response.text
        self.assertIn("/ingestion.html", html,
            "主页面缺少入库管理 (ingestion.html) 链接")

    def test_admin_page_has_backup_link(self):
        """主页面应包含「备份导出导入」(backup) 导航链接。"""
        response = self.client.get("/")
        html = response.text
        self.assertIn("/backup.html", html,
            "主页面缺少备份导出导入 (backup.html) 链接")

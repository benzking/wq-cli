"""Tests for utils.mp_api_client — error classification and fetch flow."""
import asyncio
import unittest
from unittest import mock
from utils.mp_api_client import MpApiResult, _classify_error


class TestMpApiResult(unittest.TestCase):
    def test_is_ok_with_data_and_no_error(self):
        result = MpApiResult(data={"base_resp": {"ret": 0}})
        self.assertTrue(result.is_ok)

    def test_is_not_ok_with_error_type(self):
        result = MpApiResult(error_type="frequency_control")
        self.assertFalse(result.is_ok)

    def test_is_not_ok_with_none_data(self):
        result = MpApiResult(data=None)
        self.assertFalse(result.is_ok)


class TestClassifyError(unittest.TestCase):
    def test_frequency_control(self):
        self.assertEqual(_classify_error(200013, ""), "frequency_control")

    def test_token_expired(self):
        self.assertEqual(_classify_error(200003, ""), "token_expired")

    def test_invalid_fakeid(self):
        self.assertEqual(_classify_error(200002, "invalid args"), "invalid_fakeid")

    def test_invalid_fakeid_case_insensitive(self):
        self.assertEqual(_classify_error(200002, "Invalid Args"), "invalid_fakeid")

    def test_unknown(self):
        self.assertEqual(_classify_error(99999, "some error"), "unknown")


class TestFetchMpApi(unittest.TestCase):
    def setUp(self):
        self.creds = {"token": "test", "cookie": "test"}
        self.params = {}

    def _run(self, coro):
        return asyncio.run(coro)

    @mock.patch('utils.mp_api_client._fetch_sync_curl')
    @mock.patch('utils.mp_api_client.HAS_CURL_CFFI', True)
    def test_fetch_returns_ok_on_success(self, mock_fetch):
        mock_fetch.return_value = {"base_resp": {"ret": 0}, "publish_page": "{}"}
        from utils.mp_api_client import fetch_mp_api
        result = self._run(fetch_mp_api("http://test", self.params, self.creds))
        self.assertTrue(result.is_ok)

    @mock.patch('utils.mp_api_client._fetch_sync_curl')
    @mock.patch('utils.mp_api_client.HAS_CURL_CFFI', True)
    def test_fetch_returns_frequency_control(self, mock_fetch):
        mock_fetch.return_value = {"base_resp": {"ret": 200013, "err_msg": "freq"}}
        from utils.mp_api_client import fetch_mp_api
        result = self._run(fetch_mp_api("http://test", self.params, self.creds))
        self.assertEqual(result.error_type, "frequency_control")

    @mock.patch('utils.mp_api_client._fetch_sync_curl')
    @mock.patch('utils.mp_api_client.HAS_CURL_CFFI', True)
    def test_fetch_returns_token_expired(self, mock_fetch):
        mock_fetch.return_value = {"base_resp": {"ret": 200003}}
        from utils.mp_api_client import fetch_mp_api
        result = self._run(fetch_mp_api("http://test", self.params, self.creds))
        self.assertEqual(result.error_type, "token_expired")

    @mock.patch('utils.mp_api_client._fetch_sync_curl')
    @mock.patch('utils.mp_api_client.HAS_CURL_CFFI', True)
    def test_fetch_handles_network_error(self, mock_fetch):
        mock_fetch.side_effect = Exception("Connection refused")
        from utils.mp_api_client import fetch_mp_api
        result = self._run(fetch_mp_api("http://test", self.params, self.creds))
        self.assertEqual(result.error_type, "network_error")

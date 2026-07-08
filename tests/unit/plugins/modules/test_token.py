# -*- coding: utf-8 -*-

# Copyright: (c) 2025, Samuel Assmann <samuel@tecbeat.de>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json
import pytest
from unittest.mock import Mock, patch

from ansible.module_utils import basic
from ansible.module_utils.common.text.converters import to_bytes
from ansible_collections.nils_ost.proxymanager.plugins.modules import token


def set_module_args(args):
    """Prepare arguments for Ansible module."""
    if "_ansible_remote_tmp" not in args:
        args["_ansible_remote_tmp"] = "/tmp"
    if "_ansible_keep_remote_files" not in args:
        args["_ansible_keep_remote_files"] = False

    args = json.dumps({"ANSIBLE_MODULE_ARGS": args})
    basic._ANSIBLE_ARGS = to_bytes(args)
    basic._ANSIBLE_PROFILE = "legacy"


class AnsibleExitJson(Exception):
    pass


class AnsibleFailJson(Exception):
    pass


def exit_json(*args, **kwargs):
    if "changed" not in kwargs:
        kwargs["changed"] = False
    raise AnsibleExitJson(kwargs)


def fail_json(*args, **kwargs):
    kwargs["failed"] = True
    raise AnsibleFailJson(kwargs)


@pytest.fixture
def mock_module():
    with patch.object(basic.AnsibleModule, "exit_json", exit_json):
        with patch.object(basic.AnsibleModule, "fail_json", fail_json):
            yield


class TestTokenModule:
    def test_successful_authentication_http(self, mock_module):
        set_module_args(
            {
                "url": "http://npm.example.com:81",
                "user": "admin@example.com",
                "password": "secret123",
            }
        )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"token": "test-token-12345"}

        with patch("requests.post", return_value=mock_response):
            with pytest.raises(AnsibleExitJson) as result:
                token.main()

            assert result.value.args[0]["changed"] is False
            assert result.value.args[0]["token"] == "test-token-12345"
            assert result.value.args[0]["url"] == "http://npm.example.com:81"

    def test_successful_authentication_https(self, mock_module):
        set_module_args(
            {
                "url": "https://npm.example.com:443",
                "user": "admin@example.com",
                "password": "secret123",
            }
        )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"token": "test-token-https"}

        with patch("requests.post", return_value=mock_response):
            with pytest.raises(AnsibleExitJson) as result:
                token.main()

            assert result.value.args[0]["changed"] is False
            assert result.value.args[0]["token"] == "test-token-https"
            assert result.value.args[0]["url"] == "https://npm.example.com:443"

    def test_authentication_failure_wrong_credentials(self, mock_module):
        set_module_args(
            {
                "url": "http://npm.example.com:81",
                "user": "admin@example.com",
                "password": "wrong-password",
            }
        )

        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Invalid credentials"

        with patch("requests.post", return_value=mock_response):
            with pytest.raises(AnsibleFailJson) as result:
                token.main()

            assert result.value.args[0]["failed"] is True
            assert "Authentication failed" in result.value.args[0]["msg"]

    def test_authentication_failure_missing_token(self, mock_module):
        set_module_args(
            {
                "url": "http://npm.example.com:81",
                "user": "admin@example.com",
                "password": "secret123",
            }
        )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"expires": "2025-12-31"}

        with patch("requests.post", return_value=mock_response):
            with pytest.raises(AnsibleFailJson) as result:
                token.main()

            assert result.value.args[0]["failed"] is True
            assert "does not contain a token" in result.value.args[0]["msg"]

    def test_connection_error(self, mock_module):
        set_module_args(
            {
                "url": "http://npm.example.com:81",
                "user": "admin@example.com",
                "password": "secret123",
            }
        )

        import requests

        with patch("requests.post", side_effect=requests.exceptions.ConnectionError("Connection refused")):
            with pytest.raises(AnsibleFailJson) as result:
                token.main()

            assert result.value.args[0]["failed"] is True
            assert "Connection error" in result.value.args[0]["msg"]

    def test_default_url_without_trailing_slash(self, mock_module):
        set_module_args(
            {
                "url": "http://npm.example.com:81/",
                "user": "admin@example.com",
                "password": "secret123",
            }
        )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"token": "test-token"}

        with patch("requests.post", return_value=mock_response):
            with pytest.raises(AnsibleExitJson) as result:
                token.main()

            assert result.value.args[0]["url"] == "http://npm.example.com:81"

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
from ansible_collections.nils_ost.proxymanager.plugins.modules import redirection


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
    """Exception for successful module exit."""

    pass


class AnsibleFailJson(Exception):
    """Exception for module failure."""

    pass


def exit_json(*args, **kwargs):
    """Mock exit_json for testing."""
    if "changed" not in kwargs:
        kwargs["changed"] = False
    raise AnsibleExitJson(kwargs)


def fail_json(*args, **kwargs):
    """Mock fail_json for testing."""
    kwargs["failed"] = True
    raise AnsibleFailJson(kwargs)


@pytest.fixture
def mock_module():
    """Create mock AnsibleModule."""
    with patch.object(basic.AnsibleModule, "exit_json", exit_json):
        with patch.object(basic.AnsibleModule, "fail_json", fail_json):
            yield


class TestRedirectionModule:
    """Test cases for redirection module."""

    def test_redirection_already_exists(self, mock_module):
        """Test when redirection already exists with matching config."""
        set_module_args(
            {
                "url": "http://npm.example.com:81",
                "token": "test-token",
                "domain_name": "old.example.com",
                "forward_code": 301,
                "forward_host": "https://new.example.com",
                "state": "present",
            }
        )

        mock_client = Mock()
        existing_redirection = {
            "id": 1,
            "domain_names": ["old.example.com"],
            "forward_http_code": 301,
            "forward_domain_name": "https://new.example.com",
            "preserve_path": False,
            "forward_scheme": "auto",
            "certificate_id": 0,
            "ssl_forced": False,
            "http2_support": False,
        }
        mock_client.get.return_value = [existing_redirection]

        with patch(
            "ansible_collections.nils_ost.proxymanager.plugins.modules.redirection.NginxProxyManagerClient",
            return_value=mock_client,
        ):
            with pytest.raises(AnsibleExitJson) as result:
                redirection.main()

            assert result.value.args[0]["changed"] is False
            assert result.value.args[0]["item"]["id"] == 1

    def test_create_redirection(self, mock_module):
        """Test creating a new redirection."""
        set_module_args(
            {
                "url": "http://npm.example.com:81",
                "token": "test-token",
                "domain_name": "old.example.com",
                "forward_code": 302,
                "forward_host": "https://new.example.com",
                "preserve_path": False,
                "state": "present",
            }
        )

        mock_client = Mock()
        mock_client.get.return_value = []
        mock_client.post.return_value = {
            "id": 2,
            "domain_names": ["old.example.com"],
            "forward_code": 302,
            "forward_host": "https://new.example.com",
            "preserve_path": False,
        }

        with patch(
            "ansible_collections.nils_ost.proxymanager.plugins.modules.redirection.NginxProxyManagerClient",
            return_value=mock_client,
        ):
            with pytest.raises(AnsibleExitJson) as result:
                redirection.main()

            assert result.value.args[0]["changed"] is True
            assert result.value.args[0]["item"]["id"] == 2
            mock_client.post.assert_called_once()

    def test_update_redirection(self, mock_module):
        """Test updating an existing redirection."""
        set_module_args(
            {
                "url": "http://npm.example.com:81",
                "token": "test-token",
                "domain_name": "old.example.com",
                "forward_code": 301,
                "forward_host": "https://updated.example.com",
                "state": "present",
            }
        )

        mock_client = Mock()
        mock_client.get.return_value = [
            {
                "id": 3,
                "domain_names": ["old.example.com"],
                "forward_code": 301,
                "forward_host": "https://old.example.com",
                "preserve_path": True,
            }
        ]
        mock_client.put.return_value = {
            "id": 3,
            "domain_names": ["old.example.com"],
            "forward_code": 301,
            "forward_host": "https://updated.example.com",
            "preserve_path": True,
        }

        with patch(
            "ansible_collections.nils_ost.proxymanager.plugins.modules.redirection.NginxProxyManagerClient",
            return_value=mock_client,
        ):
            with pytest.raises(AnsibleExitJson) as result:
                redirection.main()

            assert result.value.args[0]["changed"] is True
            assert (
                result.value.args[0]["item"]["forward_host"]
                == "https://updated.example.com"
            )
            mock_client.put.assert_called_once()

    def test_delete_redirection(self, mock_module):
        """Test deleting a redirection."""
        set_module_args(
            {
                "url": "http://npm.example.com:81",
                "token": "test-token",
                "domain_name": "old.example.com",
                "state": "absent",
            }
        )

        mock_client = Mock()
        mock_client.get.return_value = [
            {
                "id": 4,
                "domain_names": ["old.example.com"],
            }
        ]
        mock_client.delete.return_value = True

        with patch(
            "ansible_collections.nils_ost.proxymanager.plugins.modules.redirection.NginxProxyManagerClient",
            return_value=mock_client,
        ):
            with pytest.raises(AnsibleExitJson) as result:
                redirection.main()

            assert result.value.args[0]["changed"] is True
            assert result.value.args[0]["item"] is None
            mock_client.delete.assert_called_once_with("/api/nginx/redirection-hosts/4")

    def test_delete_nonexistent_redirection(self, mock_module):
        """Test deleting a redirection that doesn't exist."""
        set_module_args(
            {
                "url": "http://npm.example.com:81",
                "token": "test-token",
                "domain_name": "nonexistent.example.com",
                "state": "absent",
            }
        )

        mock_client = Mock()
        mock_client.get.return_value = []

        with patch(
            "ansible_collections.nils_ost.proxymanager.plugins.modules.redirection.NginxProxyManagerClient",
            return_value=mock_client,
        ):
            with pytest.raises(AnsibleExitJson) as result:
                redirection.main()

            assert result.value.args[0]["changed"] is False
            assert result.value.args[0]["item"] is None

    def test_default_values(self, mock_module):
        """Test default values for HTTP code and preserve_path."""
        set_module_args(
            {
                "url": "http://npm.example.com:81",
                "token": "test-token",
                "domain_name": "old.example.com",
                "forward_host": "https://new.example.com",
                "state": "present",
            }
        )

        mock_client = Mock()
        mock_client.get.return_value = []
        mock_client.post.return_value = {
            "id": 5,
            "domain_names": ["old.example.com"],
            "forward_http_code": 301,
            "forward_domain_name": "https://new.example.com",
            "preserve_path": False,
            "forward_scheme": "auto",
            "certificate_id": 0,
            "ssl_forced": False,
            "http2_support": False,
        }

        with patch(
            "ansible_collections.nils_ost.proxymanager.plugins.modules.redirection.NginxProxyManagerClient",
            return_value=mock_client,
        ):
            with pytest.raises(AnsibleExitJson) as result:
                redirection.main()

            # Verify defaults: 301 redirect with preserve_path=False
            call_args = mock_client.post.call_args
            payload = call_args[0][1]
            assert payload["forward_http_code"] == 301
            assert payload["preserve_path"] is False
            assert payload["forward_scheme"] == "auto"

    def test_api_error_handling(self, mock_module):
        """Test handling of API errors."""
        set_module_args(
            {
                "url": "http://npm.example.com:81",
                "token": "test-token",
                "domain_name": "old.example.com",
                "forward_host": "https://new.example.com",
                "state": "present",
            }
        )

        mock_client = Mock()
        mock_client.get.side_effect = redirection.NginxProxyManagerAPIError(
            "API Error", status_code=500, response_text="Internal Server Error"
        )

        with patch(
            "ansible_collections.nils_ost.proxymanager.plugins.modules.redirection.NginxProxyManagerClient",
            return_value=mock_client,
        ):
            with pytest.raises(AnsibleFailJson) as result:
                redirection.main()

            assert result.value.args[0]["failed"] is True
            assert "API Error" in result.value.args[0]["msg"]

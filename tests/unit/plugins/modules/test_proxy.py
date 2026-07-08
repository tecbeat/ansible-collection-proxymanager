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
from ansible_collections.nils_ost.proxymanager.plugins.modules import proxy


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


class TestProxyModule:
    """Test cases for proxy module."""

    def test_proxy_already_exists(self, mock_module):
        """Test when proxy host already exists with matching config."""
        set_module_args(
            {
                "url": "http://npm.example.com:81",
                "token": "test-token",
                "domain_name": "app.example.com",
                "forward_host": "192.168.1.100",
                "forward_port": 80,
                "state": "present",
            }
        )

        mock_client = Mock()
        existing_proxy = {
            "id": 1,
            "domain_names": ["app.example.com"],
            "forward_host": "192.168.1.100",
            "forward_port": 80,
            "forward_scheme": "http",
            "certificate_id": 0,
            "ssl_forced": False,
            "http2_support": False,
            "hsts_enabled": False,
            "hsts_subdomains": False,
            "block_exploits": False,
            "caching_enabled": False,
            "allow_websocket_upgrade": False,
            "trust_forwarded_proto": False,
            "access_list_id": 0,
            "advanced_config": "",
            "locations": [],
        }
        mock_client.get.return_value = [existing_proxy]

        with patch(
            "ansible_collections.nils_ost.proxymanager.plugins.modules.proxy.NginxProxyManagerClient",
            return_value=mock_client,
        ):
            with pytest.raises(AnsibleExitJson) as result:
                proxy.main()

            assert result.value.args[0]["changed"] is False
            assert result.value.args[0]["item"]["id"] == 1

    def test_create_proxy(self, mock_module):
        """Test creating a new proxy host."""
        set_module_args(
            {
                "url": "http://npm.example.com:81",
                "token": "test-token",
                "domain_name": "new.example.com",
                "forward_host": "192.168.1.200",
                "forward_port": 8080,
                "forward_scheme": "https",
                "state": "present",
            }
        )

        mock_client = Mock()
        mock_client.get.return_value = []
        mock_client.post.return_value = {
            "id": 2,
            "domain_names": ["new.example.com"],
            "forward_host": "192.168.1.200",
            "forward_port": 8080,
            "forward_scheme": "https",
        }

        with patch(
            "ansible_collections.nils_ost.proxymanager.plugins.modules.proxy.NginxProxyManagerClient",
            return_value=mock_client,
        ):
            with pytest.raises(AnsibleExitJson) as result:
                proxy.main()

            assert result.value.args[0]["changed"] is True
            assert result.value.args[0]["item"]["id"] == 2
            mock_client.post.assert_called_once()

    def test_create_proxy_with_ssl(self, mock_module):
        """Test creating a proxy host with SSL certificate."""
        set_module_args(
            {
                "url": "http://npm.example.com:81",
                "token": "test-token",
                "domain_name": "secure.example.com",
                "forward_host": "192.168.1.100",
                "forward_port": 80,
                "certificate_id": 5,
                "force_ssl": True,
                "http2_support": True,
                "state": "present",
            }
        )

        mock_client = Mock()
        mock_client.get.return_value = []
        mock_client.post.return_value = {
            "id": 3,
            "domain_names": ["secure.example.com"],
            "forward_host": "192.168.1.100",
            "forward_port": 80,
            "certificate_id": 5,
            "ssl_forced": True,
            "http2_support": True,
        }

        with patch(
            "ansible_collections.nils_ost.proxymanager.plugins.modules.proxy.NginxProxyManagerClient",
            return_value=mock_client,
        ):
            with pytest.raises(AnsibleExitJson) as result:
                proxy.main()

            assert result.value.args[0]["changed"] is True
            assert result.value.args[0]["item"]["certificate_id"] == 5

    def test_ssl_enabled_without_certificate(self, mock_module):
        """Test error when SSL is enabled but no certificate exists."""
        set_module_args(
            {
                "url": "http://npm.example.com:81",
                "token": "test-token",
                "domain_name": "nocert.example.com",
                "forward_host": "192.168.1.100",
                "forward_port": 80,
                "ssl_enabled": True,
                "state": "present",
            }
        )

        mock_client = Mock()
        # First call: no proxy exists
        # Second call: no certificate exists
        mock_client.get.side_effect = [[], []]

        with patch(
            "ansible_collections.nils_ost.proxymanager.plugins.modules.proxy.NginxProxyManagerClient",
            return_value=mock_client,
        ):
            with pytest.raises(AnsibleFailJson) as result:
                proxy.main()

            assert result.value.args[0]["failed"] is True
            assert "certificate" in result.value.args[0]["msg"].lower()

    def test_update_proxy(self, mock_module):
        """Test updating an existing proxy host."""
        set_module_args(
            {
                "url": "http://npm.example.com:81",
                "token": "test-token",
                "domain_name": "app.example.com",
                "forward_host": "192.168.1.100",
                "forward_port": 8080,  # Changed from 80 to 8080
                "state": "present",
            }
        )

        mock_client = Mock()
        mock_client.get.return_value = [
            {
                "id": 4,
                "domain_names": ["app.example.com"],
                "forward_host": "192.168.1.100",
                "forward_port": 80,
                "forward_scheme": "http",
                "certificate_id": 0,
                "ssl_forced": False,
                "http2_support": False,
                "hsts_enabled": False,
                "hsts_subdomains": False,
                "block_exploits": True,
                "caching_enabled": False,
                "allow_websocket_upgrade": True,
                "access_list_id": 0,
                "advanced_config": "",
                "locations": [],
            }
        ]
        mock_client.put.return_value = {
            "id": 4,
            "domain_names": ["app.example.com"],
            "forward_host": "192.168.1.100",
            "forward_port": 8080,
        }

        with patch(
            "ansible_collections.nils_ost.proxymanager.plugins.modules.proxy.NginxProxyManagerClient",
            return_value=mock_client,
        ):
            with pytest.raises(AnsibleExitJson) as result:
                proxy.main()

            assert result.value.args[0]["changed"] is True
            assert result.value.args[0]["item"]["forward_port"] == 8080
            mock_client.put.assert_called_once()

    def test_delete_proxy(self, mock_module):
        """Test deleting a proxy host."""
        set_module_args(
            {
                "url": "http://npm.example.com:81",
                "token": "test-token",
                "domain_name": "delete.example.com",
                "state": "absent",
            }
        )

        mock_client = Mock()
        mock_client.get.return_value = [
            {
                "id": 6,
                "domain_names": ["delete.example.com"],
            }
        ]
        mock_client.delete.return_value = True

        with patch(
            "ansible_collections.nils_ost.proxymanager.plugins.modules.proxy.NginxProxyManagerClient",
            return_value=mock_client,
        ):
            with pytest.raises(AnsibleExitJson) as result:
                proxy.main()

            assert result.value.args[0]["changed"] is True
            assert result.value.args[0]["item"] is None
            mock_client.delete.assert_called_once_with("/api/nginx/proxy-hosts/6")

    def test_delete_nonexistent_proxy(self, mock_module):
        """Test deleting a proxy that doesn't exist."""
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
            "ansible_collections.nils_ost.proxymanager.plugins.modules.proxy.NginxProxyManagerClient",
            return_value=mock_client,
        ):
            with pytest.raises(AnsibleExitJson) as result:
                proxy.main()

            assert result.value.args[0]["changed"] is False
            assert result.value.args[0]["item"] is None

    def test_custom_locations(self, mock_module):
        """Test proxy with custom location blocks."""
        set_module_args(
            {
                "url": "http://npm.example.com:81",
                "token": "test-token",
                "domain_name": "api.example.com",
                "forward_host": "192.168.1.100",
                "forward_port": 80,
                "locations": [
                    {
                        "path": "/api",
                        "forward_host": "192.168.1.101",
                        "forward_port": 3000,
                        "forward_scheme": "http",
                    }
                ],
                "state": "present",
            }
        )

        mock_client = Mock()
        mock_client.get.return_value = []
        mock_client.post.return_value = {
            "id": 7,
            "domain_names": ["api.example.com"],
            "forward_host": "192.168.1.100",
            "forward_port": 80,
            "locations": [
                {
                    "path": "/api",
                    "forward_host": "192.168.1.101",
                    "forward_port": 3000,
                    "forward_scheme": "http",
                }
            ],
        }

        with patch(
            "ansible_collections.nils_ost.proxymanager.plugins.modules.proxy.NginxProxyManagerClient",
            return_value=mock_client,
        ):
            with pytest.raises(AnsibleExitJson) as result:
                proxy.main()

            assert result.value.args[0]["changed"] is True
            call_args = mock_client.post.call_args
            payload = call_args[0][1]
            assert len(payload["locations"]) == 1
            assert payload["locations"][0]["path"] == "/api"

    def test_api_error_handling(self, mock_module):
        """Test handling of API errors."""
        set_module_args(
            {
                "url": "http://npm.example.com:81",
                "token": "test-token",
                "domain_name": "app.example.com",
                "forward_host": "192.168.1.100",
                "forward_port": 80,
                "state": "present",
            }
        )

        mock_client = Mock()
        mock_client.get.side_effect = proxy.NginxProxyManagerAPIError(
            "API Error", status_code=500, response_text="Internal Server Error"
        )

        with patch(
            "ansible_collections.nils_ost.proxymanager.plugins.modules.proxy.NginxProxyManagerClient",
            return_value=mock_client,
        ):
            with pytest.raises(AnsibleFailJson) as result:
                proxy.main()

            assert result.value.args[0]["failed"] is True
            assert "API Error" in result.value.args[0]["msg"]

    def test_default_values(self, mock_module):
        """Test default values are applied correctly."""
        set_module_args(
            {
                "url": "http://npm.example.com:81",
                "token": "test-token",
                "domain_name": "defaults.example.com",
                "forward_host": "192.168.1.100",
                "forward_port": 80,
                "state": "present",
            }
        )

        mock_client = Mock()
        mock_client.get.return_value = []
        mock_client.post.return_value = {
            "id": 8,
            "domain_names": ["defaults.example.com"],
            "forward_host": "192.168.1.100",
            "forward_port": 80,
            "forward_scheme": "http",
            "block_exploits": True,
            "allow_websocket_upgrade": True,
        }

        with patch(
            "ansible_collections.nils_ost.proxymanager.plugins.modules.proxy.NginxProxyManagerClient",
            return_value=mock_client,
        ):
            with pytest.raises(AnsibleExitJson) as result:
                proxy.main()

            call_args = mock_client.post.call_args
            payload = call_args[0][1]
            # Check defaults
            assert payload["forward_scheme"] == "http"
            assert payload["block_exploits"] is False
            assert payload["allow_websocket_upgrade"] is False
            assert payload["caching_enabled"] is False

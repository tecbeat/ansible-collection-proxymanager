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
from ansible_collections.nils_ost.proxymanager.plugins.modules import certificate


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


class TestCertificateModule:
    """Test cases for certificate module."""

    def test_certificate_already_exists(self, mock_module):
        """Test when certificate already exists."""
        set_module_args(
            {
                "url": "http://npm.example.com:81",
                "token": "test-token",
                "domain_name": "example.com",
                "state": "present",
            }
        )

        mock_client = Mock()
        mock_client.get.return_value = [
            {
                "id": 1,
                "domain_names": ["example.com", "*.example.com"],
                "provider": "letsencrypt",
            }
        ]

        with patch(
            "ansible_collections.nils_ost.proxymanager.plugins.modules.certificate.NginxProxyManagerClient",
            return_value=mock_client,
        ):
            with pytest.raises(AnsibleExitJson) as result:
                certificate.main()

            assert result.value.args[0]["changed"] is False
            assert result.value.args[0]["item"]["id"] == 1

    def test_create_certificate_domainoffensive(self, mock_module):
        """Test creating a certificate with domainoffensive provider."""
        set_module_args(
            {
                "url": "http://npm.example.com:81",
                "token": "test-token",
                "domain_name": "example.com",
                "provider": "domainoffensive",
                "provider_credentials": "api-token-123",
                "state": "present",
            }
        )

        mock_client = Mock()
        # First call: certificate doesn't exist
        mock_client.get.return_value = []
        # Second call: certificate created
        mock_client.post.return_value = {
            "id": 2,
            "domain_names": ["example.com", "*.example.com"],
            "provider": "letsencrypt",
        }

        with patch(
            "ansible_collections.nils_ost.proxymanager.plugins.modules.certificate.NginxProxyManagerClient",
            return_value=mock_client,
        ):
            with pytest.raises(AnsibleExitJson) as result:
                certificate.main()

            assert result.value.args[0]["changed"] is True
            assert result.value.args[0]["item"]["id"] == 2
            mock_client.post.assert_called_once()

    def test_create_certificate_without_supported_provider(self, mock_module):
        """Test trying to create certificate without supported provider."""
        set_module_args(
            {
                "url": "http://npm.example.com:81",
                "token": "test-token",
                "domain_name": "example.com",
                "provider": "other",
                "state": "present",
            }
        )

        mock_client = Mock()
        mock_client.get.return_value = []

        with patch(
            "ansible_collections.nils_ost.proxymanager.plugins.modules.certificate.NginxProxyManagerClient",
            return_value=mock_client,
        ):
            with pytest.raises(AnsibleFailJson) as result:
                certificate.main()

            assert result.value.args[0]["failed"] is True
            assert "Cannot create certificate" in result.value.args[0]["msg"]

    def test_delete_certificate(self, mock_module):
        """Test deleting a certificate."""
        set_module_args(
            {
                "url": "http://npm.example.com:81",
                "token": "test-token",
                "domain_name": "example.com",
                "state": "absent",
            }
        )

        mock_client = Mock()
        mock_client.get.return_value = [
            {
                "id": 3,
                "domain_names": ["example.com", "*.example.com"],
            }
        ]
        mock_client.delete.return_value = True

        with patch(
            "ansible_collections.nils_ost.proxymanager.plugins.modules.certificate.NginxProxyManagerClient",
            return_value=mock_client,
        ):
            with pytest.raises(AnsibleExitJson) as result:
                certificate.main()

            assert result.value.args[0]["changed"] is True
            assert result.value.args[0]["item"] is None
            mock_client.delete.assert_called_once_with("/api/nginx/certificates/3")

    def test_delete_nonexistent_certificate(self, mock_module):
        """Test deleting a certificate that doesn't exist."""
        set_module_args(
            {
                "url": "http://npm.example.com:81",
                "token": "test-token",
                "domain_name": "example.com",
                "state": "absent",
            }
        )

        mock_client = Mock()
        mock_client.get.return_value = []

        with patch(
            "ansible_collections.nils_ost.proxymanager.plugins.modules.certificate.NginxProxyManagerClient",
            return_value=mock_client,
        ):
            with pytest.raises(AnsibleExitJson) as result:
                certificate.main()

            assert result.value.args[0]["changed"] is False
            assert result.value.args[0]["item"] is None

    def test_api_error_handling(self, mock_module):
        """Test handling of API errors."""
        set_module_args(
            {
                "url": "http://npm.example.com:81",
                "token": "test-token",
                "domain_name": "example.com",
                "state": "present",
            }
        )

        mock_client = Mock()
        mock_client.get.side_effect = certificate.NginxProxyManagerAPIError(
            "API Error", status_code=500, response_text="Internal Server Error"
        )

        with patch(
            "ansible_collections.nils_ost.proxymanager.plugins.modules.certificate.NginxProxyManagerClient",
            return_value=mock_client,
        ):
            with pytest.raises(AnsibleFailJson) as result:
                certificate.main()

            assert result.value.args[0]["failed"] is True
            assert "API Error" in result.value.args[0]["msg"]

    def test_missing_credentials_for_domainoffensive(self, mock_module):
        """Test error when credentials are missing for domainoffensive."""
        set_module_args(
            {
                "url": "http://npm.example.com:81",
                "token": "test-token",
                "domain_name": "example.com",
                "provider": "domainoffensive",
                "state": "present",
            }
        )

        mock_client = Mock()
        mock_client.get.return_value = []

        with patch(
            "ansible_collections.nils_ost.proxymanager.plugins.modules.certificate.NginxProxyManagerClient",
            return_value=mock_client,
        ):
            with pytest.raises(AnsibleFailJson) as result:
                certificate.main()

            assert result.value.args[0]["failed"] is True
            assert "credentials" in result.value.args[0]["msg"].lower()

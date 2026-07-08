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
from ansible_collections.nils_ost.proxymanager.plugins.modules import access_list


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


BASE_ARGS = {
    "url": "http://npm.example.com:81",
    "token": "test-token",
    "name": "internal",
}


class TestAccessListModule:
    """Tests for the access_list module."""

    def test_create_new_access_list(self, mock_module):
        """When no matching list exists, POST is called and changed=True."""
        set_module_args({**BASE_ARGS, "state": "present"})

        mock_client = Mock()
        mock_client.get.return_value = []
        mock_client.post.return_value = {
            "id": 42,
            "name": "internal",
            "satisfy_any": False,
            "pass_auth": False,
            "items": [],
            "clients": [],
        }

        with patch(
            "ansible_collections.nils_ost.proxymanager.plugins."
            "modules.access_list.NginxProxyManagerClient",
            return_value=mock_client,
        ):
            with pytest.raises(AnsibleExitJson) as result:
                access_list.main()

        assert result.value.args[0]["changed"] is True
        assert result.value.args[0]["item"]["id"] == 42
        mock_client.post.assert_called_once()

    def test_absent_already_absent(self, mock_module):
        """Deleting a non-existent list is a no-op."""
        set_module_args({**BASE_ARGS, "state": "absent"})

        mock_client = Mock()
        mock_client.get.return_value = []

        with patch(
            "ansible_collections.nils_ost.proxymanager.plugins."
            "modules.access_list.NginxProxyManagerClient",
            return_value=mock_client,
        ):
            with pytest.raises(AnsibleExitJson) as result:
                access_list.main()

        assert result.value.args[0]["changed"] is False
        mock_client.delete.assert_not_called()

    def test_absent_deletes_existing(self, mock_module):
        """Deleting an existing list calls DELETE and reports changed=True."""
        set_module_args({**BASE_ARGS, "state": "absent"})

        mock_client = Mock()
        mock_client.get.return_value = [
            {"id": 7, "name": "internal", "items": [], "clients": []}
        ]

        with patch(
            "ansible_collections.nils_ost.proxymanager.plugins."
            "modules.access_list.NginxProxyManagerClient",
            return_value=mock_client,
        ):
            with pytest.raises(AnsibleExitJson) as result:
                access_list.main()

        assert result.value.args[0]["changed"] is True
        mock_client.delete.assert_called_once_with(
            "/api/nginx/access-lists/7"
        )

    def test_present_no_change_when_matching(self, mock_module):
        """Existing list matching the desired state -> changed=False."""
        set_module_args(
            {
                **BASE_ARGS,
                "state": "present",
                "satisfy_any": True,
                "pass_auth": False,
                "clients": [
                    {"address": "10.0.0.0/8", "directive": "allow"},
                ],
            }
        )

        mock_client = Mock()
        mock_client.get.return_value = [
            {
                "id": 3,
                "name": "internal",
                "satisfy_any": True,
                "pass_auth": False,
                "items": [],
                "clients": [
                    {"address": "10.0.0.0/8", "directive": "allow"}
                ],
            }
        ]

        with patch(
            "ansible_collections.nils_ost.proxymanager.plugins."
            "modules.access_list.NginxProxyManagerClient",
            return_value=mock_client,
        ):
            with pytest.raises(AnsibleExitJson) as result:
                access_list.main()

        assert result.value.args[0]["changed"] is False
        assert result.value.args[0]["item"]["id"] == 3
        mock_client.put.assert_not_called()
        mock_client.post.assert_not_called()

    def test_present_updates_on_client_drift(self, mock_module):
        """Different client rules -> PUT and changed=True."""
        set_module_args(
            {
                **BASE_ARGS,
                "state": "present",
                "clients": [
                    {"address": "10.0.0.0/8", "directive": "allow"},
                    {"address": "192.168.0.0/16", "directive": "allow"},
                ],
            }
        )

        mock_client = Mock()
        mock_client.get.return_value = [
            {
                "id": 3,
                "name": "internal",
                "satisfy_any": False,
                "pass_auth": False,
                "items": [],
                "clients": [
                    {"address": "10.0.0.0/8", "directive": "allow"}
                ],
            }
        ]
        mock_client.put.return_value = {
            "id": 3,
            "name": "internal",
            "satisfy_any": False,
            "pass_auth": False,
            "items": [],
            "clients": [
                {"address": "10.0.0.0/8", "directive": "allow"},
                {"address": "192.168.0.0/16", "directive": "allow"},
            ],
        }

        with patch(
            "ansible_collections.nils_ost.proxymanager.plugins."
            "modules.access_list.NginxProxyManagerClient",
            return_value=mock_client,
        ):
            with pytest.raises(AnsibleExitJson) as result:
                access_list.main()

        assert result.value.args[0]["changed"] is True
        mock_client.put.assert_called_once()
        called_endpoint = mock_client.put.call_args[0][0]
        assert called_endpoint == "/api/nginx/access-lists/3"

    def test_present_password_always_drifts(self, mock_module):
        """
        NPM stores basic-auth passwords hashed and never returns the plain
        text. When the caller supplies items with a password, the module
        cannot verify a match and MUST re-submit -> changed=True.
        """
        set_module_args(
            {
                **BASE_ARGS,
                "state": "present",
                "items": [
                    {"username": "alice", "password": "s3cret"},
                ],
            }
        )

        mock_client = Mock()
        mock_client.get.return_value = [
            {
                "id": 5,
                "name": "internal",
                "satisfy_any": False,
                "pass_auth": False,
                "items": [
                    {"username": "alice", "password": "", "hint": "s****"}
                ],
                "clients": [],
            }
        ]
        mock_client.put.return_value = {"id": 5, "name": "internal"}

        with patch(
            "ansible_collections.nils_ost.proxymanager.plugins."
            "modules.access_list.NginxProxyManagerClient",
            return_value=mock_client,
        ):
            with pytest.raises(AnsibleExitJson) as result:
                access_list.main()

        assert result.value.args[0]["changed"] is True
        mock_client.put.assert_called_once()

    def test_check_mode_create(self, mock_module):
        """check_mode: no POST is issued but changed=True is reported."""
        set_module_args(
            {**BASE_ARGS, "state": "present", "_ansible_check_mode": True}
        )

        mock_client = Mock()
        mock_client.get.return_value = []

        with patch(
            "ansible_collections.nils_ost.proxymanager.plugins."
            "modules.access_list.NginxProxyManagerClient",
            return_value=mock_client,
        ):
            with pytest.raises(AnsibleExitJson) as result:
                access_list.main()

        assert result.value.args[0]["changed"] is True
        mock_client.post.assert_not_called()

    def test_get_uses_expand_query(self, mock_module):
        """The initial GET must expand items and clients to allow drift diff."""
        set_module_args({**BASE_ARGS, "state": "absent"})

        mock_client = Mock()
        mock_client.get.return_value = []

        with patch(
            "ansible_collections.nils_ost.proxymanager.plugins."
            "modules.access_list.NginxProxyManagerClient",
            return_value=mock_client,
        ):
            with pytest.raises(AnsibleExitJson):
                access_list.main()

        mock_client.get.assert_called_once_with(
            "/api/nginx/access-lists?expand=items,clients"
        )

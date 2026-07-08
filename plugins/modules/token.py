#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2025, Nils Ost (@nils-ost)
# Copyright: (c) 2025, Samuel Assmann <samuel@tecbeat.de>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Ansible module for authenticating with Nginx Proxy Manager API.

This module obtains an authentication token from a Nginx Proxy Manager instance,
which is required for all other modules in this collection.
"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: token

short_description: Authenticate with Nginx Proxy Manager API

version_added: "1.0.0"

description:
    - Authenticates with an Nginx Proxy Manager instance and returns an API token.
    - This token is required for authentication with other modules in this collection.
    - The token can be registered and passed to other modules via the token parameter.

options:
    url:
        description:
            - Base URL of the Nginx Proxy Manager instance.
        type: str
        required: true
    user:
        description:
            - Username (email address) for authentication.
        type: str
        required: true
    password:
        description:
            - Password for authentication.
        type: str
        required: true

author:
    - Nils Ost (@nils-ost)
    - Samuel Assmann (@tecbeat)

seealso:
    - module: nils_ost.proxymanager.proxy
    - module: nils_ost.proxymanager.certificate
    - module: nils_ost.proxymanager.redirection
"""

EXAMPLES = r"""
- name: Authenticate with Nginx Proxy Manager
  nils_ost.proxymanager.token:
    url: "http://{{ npm_host }}:81"
    user: "admin@example.com"
    password: "{{ npm_password }}"
  register: npm
  delegate_to: localhost

- name: Authenticate with Nginx Proxy Manager over HTTPS
  nils_ost.proxymanager.token:
    url: "https://npm.example.com"
    user: "admin@example.com"
    password: "{{ npm_password }}"
  register: npm
  delegate_to: localhost

- name: Use token in subsequent tasks
  nils_ost.proxymanager.proxy:
    url: "{{ npm.url }}"
    token: "{{ npm.token }}"
    domain_name: "example.com"
    forward_host: "192.168.1.100"
    forward_port: 80
    state: present
  delegate_to: localhost
"""

RETURN = r"""
url:
    description:
        - Full URL of the Nginx Proxy Manager instance.
        - This can be used with other modules in the collection.
    type: str
    returned: always
    sample: 'http://192.168.1.10:81'
token:
    description:
        - Authentication token for API access.
        - This token should be passed to other modules via the token parameter.
    type: str
    returned: always
    sample: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.nils_ost.proxymanager.plugins.module_utils.client import (
    NginxProxyManagerAuthError,
    NginxProxyManagerError,
    authenticate,
)


def run_module():
    """
    Execute the token authentication module.

    Validates the input parameters, obtains an API token from Nginx Proxy
    Manager via the shared ``authenticate`` helper, and returns the token
    to be reused by other modules in the collection.
    """
    module_args = dict(
        url=dict(type="str", required=True),
        user=dict(type="str", required=True),
        password=dict(type="str", required=True, no_log=True),
    )

    result = dict(
        changed=False,
        url="",
        token="",
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True,
    )

    try:
        normalised_url, token = authenticate(
            module.params["url"],
            module.params["user"],
            module.params["password"],
        )
    except ImportError as exc:
        module.fail_json(msg=str(exc), **result)
    except NginxProxyManagerAuthError as exc:
        result["url"] = module.params["url"].rstrip("/")
        module.fail_json(msg=str(exc), **result)
    except NginxProxyManagerError as exc:
        result["url"] = module.params["url"].rstrip("/")
        module.fail_json(msg=str(exc), **result)

    result["url"] = normalised_url
    result["token"] = token
    module.exit_json(**result)


def main():
    """Module entry point for Ansible execution."""
    run_module()


if __name__ == "__main__":
    main()

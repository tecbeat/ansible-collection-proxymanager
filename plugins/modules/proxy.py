#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2025, Nils Ost (@nils-ost)
# Copyright: (c) 2025, Samuel Assmann <samuel@tecbeat.de>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: proxy

author:
    - Nils Ost (@nils-ost)
    - Samuel Assmann (@tecbeat)

version_added: "1.0.0"

short_description: Manage Nginx Proxy Manager proxy hosts

description:
    - Create, update, or delete proxy hosts in Nginx Proxy Manager.
    - A proxy host forwards HTTP/HTTPS traffic from a domain to a backend service.
    - Supports SSL certificates, custom nginx configuration, and custom location blocks.

extends_documentation_fragment:
    - nils_ost.proxymanager.auth

options:
    domain_name:
        description:
            - Domain name to be proxied.
            - This is the domain that will be matched for incoming requests.
        required: true
        type: str
    forward_host:
        description:
            - Backend destination hostname or IP address.
            - Required when state is present.
        required: false
        type: str
    forward_scheme:
        description:
            - Protocol to use for communication with the backend.
        required: false
        type: str
        default: http
        choices: ['http', 'https']
    forward_port:
        description:
            - Backend destination port number.
        required: false
        type: int
        default: 80
    enable_caching:
        description:
            - Whether to enable asset caching.
        required: false
        type: bool
        default: false
    allow_websockets:
        description:
            - Whether to enable WebSocket support.
        required: false
        type: bool
        default: false
    certificate_id:
        description:
            - ID of the SSL certificate to use.
            - Use 0 for no certificate (HTTP only).
        required: false
        type: int
        default: 0
    force_ssl:
        description:
            - Whether to force SSL (redirect HTTP to HTTPS).
            - Requires a valid certificate_id.
        required: false
        type: bool
        default: false
    http2_support:
        description:
            - Whether to enable HTTP/2 support.
            - Requires a valid certificate_id.
        required: false
        type: bool
        default: false
    hsts_enabled:
        description:
            - Whether to enable HTTP Strict Transport Security (HSTS).
            - Requires force_ssl to be true.
        required: false
        type: bool
        default: false
    hsts_subdomains:
        description:
            - Whether HSTS should apply to subdomains.
            - Requires both hsts_enabled and force_ssl to be true.
        required: false
        type: bool
        default: false
    trust_forwarded_proto:
        description:
            - Whether to trust the X-Forwarded-Proto header.
        required: false
        type: bool
        default: false
    advanced_config:
        description:
            - Custom nginx configuration to include in the proxy host block.
            - Will be inserted into the server block.
        required: false
        type: str
        default: ''
    block_exploits:
        description:
            - Whether to block common exploit attempts.
        required: false
        type: bool
        default: false
    access_list_id:
        description:
            - ID of the access list to apply.
            - Use 0 for no access restrictions.
        required: false
        type: int
        default: 0
    locations:
        description:
            - List of custom location blocks for the proxy host.
            - Each location can forward to different backends.
        required: false
        type: list
        elements: dict
        default: []
        suboptions:
            path:
                description:
                    - URL path for this location block.
                    - For example /api or /admin.
                required: true
                type: str
            forward_scheme:
                description:
                    - Protocol to use for this location.
                required: false
                type: str
                default: http
                choices: ['http', 'https']
            forward_host:
                description:
                    - Backend destination host for this location.
                required: true
                type: str
            forward_port:
                description:
                    - Backend destination port for this location.
                required: true
                type: int
            advanced_config:
                description:
                    - Custom nginx configuration for this location block.
                required: false
                type: str
                default: ''
    state:
        description:
            - Desired state of the proxy host.
        required: false
        type: str
        default: present
        choices: ['absent', 'present']
"""

EXAMPLES = r"""
- name: Create basic proxy host
  nils_ost.proxymanager.proxy:
    url: "{{ npm.url }}"
    token: "{{ npm.token }}"
    domain_name: "example.com"
    forward_host: "192.168.1.100"
    forward_port: 8080
    state: present
  delegate_to: localhost

- name: Create proxy with SSL certificate
  nils_ost.proxymanager.proxy:
    url: "{{ npm.url }}"
    token: "{{ npm.token }}"
    domain_name: "secure.example.com"
    forward_host: "192.168.1.100"
    forward_port: 8080
    certificate_id: "{{ cert.item.id }}"
    force_ssl: true
    state: present
  delegate_to: localhost

- name: Create proxy with HSTS and security features
  nils_ost.proxymanager.proxy:
    url: "{{ npm.url }}"
    token: "{{ npm.token }}"
    domain_name: "secure.example.com"
    forward_host: "192.168.1.100"
    forward_port: 443
    forward_scheme: https
    certificate_id: "{{ cert.item.id }}"
    force_ssl: true
    hsts_enabled: true
    hsts_subdomains: true
    block_exploits: true
    http2_support: true
    state: present
  delegate_to: localhost

- name: Create proxy with custom nginx configuration
  nils_ost.proxymanager.proxy:
    url: "{{ npm.url }}"
    token: "{{ npm.token }}"
    domain_name: "custom.example.com"
    forward_host: "192.168.1.100"
    forward_port: 8080
    advanced_config: |
      client_max_body_size 100M;
      proxy_read_timeout 300s;
    access_list_id: 1
    state: present
  delegate_to: localhost

- name: Create proxy with custom location blocks
  nils_ost.proxymanager.proxy:
    url: "{{ npm.url }}"
    token: "{{ npm.token }}"
    domain_name: "app.example.com"
    forward_host: "192.168.1.100"
    forward_port: 80
    certificate_id: "{{ cert.item.id }}"
    force_ssl: true
    locations:
      - path: "/api"
        forward_scheme: "http"
        forward_host: "192.168.1.200"
        forward_port: 8080
        advanced_config: "proxy_read_timeout 300s;"
      - path: "/admin"
        forward_scheme: "https"
        forward_host: "192.168.1.201"
        forward_port: 443
    state: present
  delegate_to: localhost

- name: Update proxy to enable caching
  nils_ost.proxymanager.proxy:
    url: "{{ npm.url }}"
    token: "{{ npm.token }}"
    domain_name: "example.com"
    forward_host: "192.168.1.100"
    forward_port: 8080
    enable_caching: true
    allow_websockets: true
    state: present
  delegate_to: localhost

- name: Delete proxy host
  nils_ost.proxymanager.proxy:
    url: "{{ npm.url }}"
    token: "{{ npm.token }}"
    domain_name: "example.com"
    state: absent
  delegate_to: localhost
"""

RETURN = r"""
item:
    description:
        - The proxy host item that was created, updated, or found.
        - Returns null when state is absent or in case of errors.
    type: dict
    returned: when state=present
    sample:
        id: 1
        created_on: "2025-01-01 12:00:00"
        modified_on: "2025-01-01 12:00:00"
        owner_user_id: 1
        domain_names:
            - example.com
        forward_host: "192.168.1.100"
        forward_port: 8080
        forward_scheme: "http"
        access_list_id: 0
        certificate_id: 0
        ssl_forced: false
        caching_enabled: false
        block_exploits: false
        advanced_config: ""
        meta: {}
        allow_websocket_upgrade: false
        http2_support: false
        hsts_enabled: false
        hsts_subdomains: false
        enabled: true
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.nils_ost.proxymanager.plugins.module_utils.client import (  # noqa: E402
    NginxProxyManagerAPIError,
    NginxProxyManagerAuthError,
    NginxProxyManagerClient,
    NginxProxyManagerError,
    NginxProxyManagerNotFoundError,
    compare_dicts,
    search_by_domain,
)

__all__ = [
    "NginxProxyManagerAPIError",
    "NginxProxyManagerAuthError",
    "NginxProxyManagerClient",
    "NginxProxyManagerError",
    "NginxProxyManagerNotFoundError",
    "compare_dicts",
    "search_by_domain",
    "validate_ssl_dependencies",
]


def validate_ssl_dependencies(params):
    """
    Validate SSL-dependent parameters and return validation errors.

    Args:
        params: Dictionary of module parameters

    Returns:
        list: List of error messages (empty if valid)
    """
    errors = []

    if params.get("hsts_enabled") and not params.get("force_ssl"):
        errors.append(
            "hsts_enabled requires force_ssl to be true. "
            "HSTS (HTTP Strict Transport Security) only works with SSL/TLS enabled."
        )

    if params.get("hsts_subdomains") and not params.get("hsts_enabled"):
        errors.append(
            "hsts_subdomains requires hsts_enabled to be true. "
            "Enable HSTS first before including subdomains."
        )

    if params.get("hsts_subdomains") and not params.get("force_ssl"):
        errors.append(
            "hsts_subdomains requires force_ssl to be true. "
            "HSTS subdomains only work with SSL/TLS enabled."
        )

    if params.get("force_ssl") and params.get("certificate_id", 0) == 0:
        errors.append(
            "force_ssl requires a valid certificate_id (currently 0). "
            "Please specify a certificate_id to enable SSL."
        )

    if params.get("http2_support") and params.get("certificate_id", 0) == 0:
        errors.append(
            "http2_support requires a valid certificate_id (currently 0). "
            "HTTP/2 is typically used with TLS and requires a certificate."
        )

    return errors


def run_module():
    """
    Execute the proxy module.

    This function handles the main logic for managing proxy hosts.
    It validates input parameters, manages API communication, and ensures
    idempotent create/update/delete operations.
    """
    module_args = dict(
        url=dict(type="str", required=True),
        token=dict(type="str", required=True, no_log=True),
        domain_name=dict(type="str", required=True),
        forward_host=dict(type="str", required=False, default=None),
        forward_scheme=dict(
            type="str",
            required=False,
            default="http",
            choices=["http", "https"],
        ),
        forward_port=dict(type="int", required=False, default=80),
        enable_caching=dict(type="bool", required=False, default=False),
        allow_websockets=dict(type="bool", required=False, default=False),
        certificate_id=dict(type="int", required=False, default=0),
        force_ssl=dict(type="bool", required=False, default=False),
        http2_support=dict(type="bool", required=False, default=False),
        hsts_enabled=dict(type="bool", required=False, default=False),
        hsts_subdomains=dict(type="bool", required=False, default=False),
        trust_forwarded_proto=dict(type="bool", required=False, default=False),
        advanced_config=dict(type="str", required=False, default=""),
        block_exploits=dict(type="bool", required=False, default=False),
        access_list_id=dict(type="int", required=False, default=0),
        locations=dict(
            type="list",
            required=False,
            default=[],
            elements="dict",
            options=dict(
                path=dict(type="str", required=True),
                forward_scheme=dict(
                    type="str",
                    required=False,
                    default="http",
                    choices=["http", "https"],
                ),
                forward_host=dict(type="str", required=True),
                forward_port=dict(type="int", required=True),
                advanced_config=dict(type="str", required=False, default=""),
            ),
        ),
        state=dict(type="str", default="present", choices=["absent", "present"]),
    )

    result = dict(changed=False, item=None)

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    try:
        if (
            module.params["state"] == "present"
            and module.params.get("forward_host") is None
        ):
            module.fail_json(
                msg='"forward_host" is required when state is "present"', **result
            )

        if module.params["state"] == "present":
            validation_errors = validate_ssl_dependencies(module.params)
            if validation_errors:
                module.fail_json(
                    msg="SSL configuration validation failed: "
                    + "; ".join(validation_errors),
                    **result,
                )

        client = NginxProxyManagerClient(module.params["url"], module.params["token"])

        items = client.get("/api/nginx/proxy-hosts")
        item = search_by_domain(items, module.params["domain_name"])

        if module.params["state"] == "present":
            data = dict(
                domain_names=[module.params["domain_name"]],
                forward_scheme=module.params["forward_scheme"],
                forward_host=module.params["forward_host"],
                forward_port=module.params["forward_port"],
                caching_enabled=module.params["enable_caching"],
                allow_websocket_upgrade=module.params["allow_websockets"],
                certificate_id=module.params["certificate_id"],
                ssl_forced=module.params["force_ssl"],
                http2_support=module.params["http2_support"],
                hsts_enabled=module.params["hsts_enabled"],
                hsts_subdomains=module.params["hsts_subdomains"],
                trust_forwarded_proto=module.params["trust_forwarded_proto"],
                advanced_config=module.params["advanced_config"],
                block_exploits=module.params["block_exploits"],
                access_list_id=module.params["access_list_id"],
                locations=module.params["locations"],
                meta={},
            )

            compare_keys = [
                "domain_names",
                "forward_scheme",
                "forward_host",
                "forward_port",
                "caching_enabled",
                "allow_websocket_upgrade",
                "certificate_id",
                "ssl_forced",
                "http2_support",
                "hsts_enabled",
                "hsts_subdomains",
                "trust_forwarded_proto",
                "advanced_config",
                "block_exploits",
                "access_list_id",
                "locations",
            ]

            if item is None:
                if not module.check_mode:
                    item = client.post("/api/nginx/proxy-hosts", data)
                    result["changed"] = True
                    result["item"] = item
                    module.exit_json(msg="Created proxy host: {0}".format(item["id"]), **result)
                else:
                    result["changed"] = True
                    result["item"] = data
                    module.exit_json(msg="Would have created proxy host", **result)
            else:
                if not module.check_mode:
                    if compare_dicts(data, item, compare_keys):
                        result["item"] = item
                        module.exit_json(
                            msg="Proxy host already configured: {0}".format(item["id"]), **result
                        )
                    item = client.put("/api/nginx/proxy-hosts/{0}".format(item["id"]), data)
                    result["changed"] = True
                    result["item"] = item
                    module.exit_json(msg="Updated proxy host: {0}".format(item["id"]), **result)
                else:
                    result["changed"] = not compare_dicts(data, item, compare_keys)
                    result["item"] = data
                    module.exit_json(
                        msg="Would have updated proxy host: {0}".format(item["id"]), **result
                    )
        else:
            if item is None:
                module.exit_json(msg="Proxy host already absent", **result)
            if not module.check_mode:
                client.delete("/api/nginx/proxy-hosts/{0}".format(item["id"]))
                result["changed"] = True
                module.exit_json(msg="Deleted proxy host", **result)
            else:
                result["changed"] = True
                module.exit_json(msg="Would have deleted proxy host", **result)

    except NginxProxyManagerAPIError as e:
        error_msg = "API error: {0} (HTTP {1})".format(str(e), e.status_code)
        if e.response_text:
            error_msg += " - Response: {0}".format(e.response_text)
        module.fail_json(
            msg=error_msg,
            **result,
        )
    except NginxProxyManagerError as e:
        module.fail_json(msg="Nginx Proxy Manager error: {0}".format(str(e)), **result)


def main():
    """Module entry point for Ansible execution."""
    run_module()


if __name__ == "__main__":
    main()

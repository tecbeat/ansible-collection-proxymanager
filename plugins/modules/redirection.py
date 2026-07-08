#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2025, Nils Ost (@nils-ost)
# Copyright: (c) 2025, Samuel Assmann <samuel@tecbeat.de>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: redirection

short_description: Manage HTTP redirections in Nginx Proxy Manager

version_added: "1.0.0"

description:
    - Create, update, or delete HTTP redirection hosts in Nginx Proxy Manager.
    - Redirects can preserve the requested path or redirect to a fixed destination.
    - Supports multiple HTTP redirect status codes (301, 302, 307, 308, etc.).
    - Can optionally force SSL and enable HTTP/2 support.

extends_documentation_fragment:
    - nils_ost.proxymanager.auth

options:
    domain_name:
        description:
            - Domain name to redirect from.
        type: str
        required: true
    forward_host:
        description:
            - Destination URL or domain to redirect to.
            - Required when state is present.
            - Can include port number, for example example.com:8080.
        type: str
        required: false
    forward_code:
        description:
            - HTTP status code for the redirection.
            - 301 is Moved Permanently (default, recommended for SEO).
            - 302 is Found (temporary redirect).
            - 307 is Temporary Redirect (preserves HTTP method).
            - 308 is Permanent Redirect (preserves HTTP method).
        type: int
        required: false
        default: 301
        choices: [300, 301, 302, 303, 307, 308]
    forward_scheme:
        description:
            - Protocol scheme for the redirection destination.
            - auto determines the scheme automatically from the request.
            - http forces HTTP.
            - https forces HTTPS.
        type: str
        required: false
        default: 'auto'
        choices: ['auto', 'http', 'https']
    preserve_path:
        description:
            - Whether to preserve the requested path in the redirection.
            - If true, the requested path is appended to the forward host.
            - If false, all requests redirect to the exact forward host.
        type: bool
        required: false
        default: false
    certificate_id:
        description:
            - ID of the SSL certificate to use for HTTPS.
            - Set to 0 to use no certificate (HTTP only).
            - Required when force_ssl is true.
        type: int
        required: false
        default: 0
    force_ssl:
        description:
            - Force redirect HTTP requests to HTTPS.
        type: bool
        required: false
        default: false
    http2_support:
        description:
            - Enable HTTP/2 protocol support.
        type: bool
        required: false
        default: false
    state:
        description:
            - Desired state of the redirection host.
            - present ensures the redirection exists (creates or updates).
            - absent ensures the redirection is deleted.
        type: str
        required: false
        default: 'present'
        choices: ['absent', 'present']

author:
    - Nils Ost (@nils-ost)
    - Samuel Assmann (@tecbeat)

seealso:
    - module: nils_ost.proxymanager.token
    - module: nils_ost.proxymanager.proxy
    - module: nils_ost.proxymanager.certificate
"""

EXAMPLES = r"""
- name: Create simple HTTP redirection
  nils_ost.proxymanager.redirection:
    url: "{{ npm.url }}"
    token: "{{ npm.token }}"
    domain_name: "old.example.com"
    forward_host: "new.example.com"
    state: present
  delegate_to: localhost

- name: Create redirection with path preservation
  nils_ost.proxymanager.redirection:
    url: "{{ npm.url }}"
    token: "{{ npm.token }}"
    domain_name: "redirect.example.com"
    forward_host: "destination.example.com"
    forward_code: 301
    preserve_path: true
    state: present
  delegate_to: localhost

- name: Create HTTPS redirection with custom status code
  nils_ost.proxymanager.redirection:
    url: "{{ npm.url }}"
    token: "{{ npm.token }}"
    domain_name: "temp-redirect.example.com"
    forward_host: "new-location.example.com"
    forward_code: 302
    forward_scheme: https
    certificate_id: "{{ cert.item.id }}"
    force_ssl: true
    http2_support: true
    state: present
  delegate_to: localhost

- name: Update existing redirection
  nils_ost.proxymanager.redirection:
    url: "{{ npm.url }}"
    token: "{{ npm.token }}"
    domain_name: "redirect.example.com"
    forward_host: "updated-destination.example.com"
    forward_code: 308
    preserve_path: true
    state: present
  delegate_to: localhost

- name: Delete redirection
  nils_ost.proxymanager.redirection:
    url: "{{ npm.url }}"
    token: "{{ npm.token }}"
    domain_name: "old.example.com"
    state: absent
  delegate_to: localhost
"""

RETURN = r"""
item:
    description:
        - Redirection host object from Nginx Proxy Manager.
        - Contains details like redirection ID, domain names, forward settings, etc.
        - Returns null when redirection is deleted or in check mode for creation.
    type: dict
    returned: when redirection exists or is created
    sample:
        id: 1
        created_on: "2025-01-15 10:30:00"
        modified_on: "2025-01-15 10:30:00"
        domain_names:
            - "old.example.com"
        forward_http_code: 301
        forward_scheme: "https"
        forward_domain_name: "new.example.com"
        preserve_path: true
        certificate_id: 1
        ssl_forced: false
        http2_support: false
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.nils_ost.proxymanager.plugins.module_utils.client import (
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
]


def run_module():
    """
    Execute the redirection module.

    This function handles the main logic for managing HTTP redirections.
    It validates input parameters, manages API communication, and ensures
    idempotent create/update/delete operations.
    """
    module_args = dict(
        url=dict(type="str", required=True),
        token=dict(type="str", required=True, no_log=True),
        domain_name=dict(type="str", required=True),
        forward_host=dict(type="str", required=False, default=None),
        forward_code=dict(
            type="int",
            required=False,
            default=301,
            choices=[300, 301, 302, 303, 307, 308],
        ),
        forward_scheme=dict(
            type="str",
            required=False,
            default="auto",
            choices=["auto", "http", "https"],
        ),
        preserve_path=dict(type="bool", required=False, default=False),
        certificate_id=dict(type="int", required=False, default=0),
        force_ssl=dict(type="bool", required=False, default=False),
        http2_support=dict(type="bool", required=False, default=False),
        state=dict(type="str", default="present", choices=["absent", "present"]),
    )

    result = dict(
        changed=False,
        item=None,
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True,
    )

    try:
        if (
            module.params["state"] == "present"
            and module.params.get("forward_host") is None
        ):
            module.fail_json(
                msg="'forward_host' is required when state is 'present'",
                **result,
            )

        if module.params["state"] == "present":
            errors = []

            if module.params.get("force_ssl") and module.params.get("certificate_id", 0) == 0:
                errors.append(
                    "force_ssl requires a valid certificate_id (currently 0). "
                    "Please specify a certificate_id to enable SSL."
                )

            if module.params.get("http2_support") and module.params.get("certificate_id", 0) == 0:
                errors.append(
                    "http2_support requires a valid certificate_id (currently 0). "
                    "HTTP/2 is typically used with TLS and requires a certificate."
                )

            if errors:
                module.fail_json(
                    msg="SSL configuration validation failed: " + "; ".join(errors),
                    **result,
                )

        client = NginxProxyManagerClient(
            url=module.params["url"],
            token=module.params["token"],
        )

        redirections = client.get("/api/nginx/redirection-hosts")
        item = search_by_domain(redirections, module.params["domain_name"])

        if module.params["state"] == "present":
            data = dict(
                domain_names=[module.params["domain_name"]],
                forward_http_code=module.params["forward_code"],
                forward_scheme=module.params["forward_scheme"],
                forward_domain_name=module.params["forward_host"],
                preserve_path=module.params["preserve_path"],
                certificate_id=module.params["certificate_id"],
                ssl_forced=module.params["force_ssl"],
                http2_support=module.params["http2_support"],
                advanced_config="",
                block_exploits=False,
                hsts_enabled=False,
                hsts_subdomains=False,
                meta={},
            )

            if item is None:
                if not module.check_mode:
                    item = client.post("/api/nginx/redirection-hosts", data)
                    result["changed"] = True
                    result["item"] = item
                    module.exit_json(
                        msg="Created redirection with ID {0}".format(item["id"]), **result
                    )
                else:
                    result["changed"] = True
                    result["item"] = data
                    module.exit_json(msg="Would have created redirection", **result)

            else:
                comparison_keys = [
                    "domain_names",
                    "forward_http_code",
                    "forward_scheme",
                    "forward_domain_name",
                    "preserve_path",
                    "certificate_id",
                    "ssl_forced",
                    "http2_support",
                ]

                if not module.check_mode:
                    if compare_dicts(data, item, comparison_keys):
                        result["item"] = item
                        module.exit_json(
                            msg="Redirection already as expected with ID {0}".format(item["id"]),
                            **result,
                        )

                    item = client.put(
                        "/api/nginx/redirection-hosts/{0}".format(item["id"]), data
                    )
                    result["changed"] = True
                    result["item"] = item
                    module.exit_json(
                        msg="Updated redirection with ID {0}".format(item["id"]), **result
                    )
                else:
                    result["changed"] = True
                    result["item"] = data
                    module.exit_json(
                        msg="Would have updated redirection with ID {0}".format(item["id"]),
                        **result,
                    )

        else:  # state == 'absent'
            if item is None:
                module.exit_json(
                    msg="Redirection already deleted or does not exist", **result
                )

            if not module.check_mode:
                client.delete("/api/nginx/redirection-hosts/{0}".format(item["id"]))
                result["changed"] = True
                module.exit_json(
                    msg="Deleted redirection with ID {0}".format(item["id"]), **result
                )
            else:
                result["changed"] = True
                module.exit_json(
                    msg="Would have deleted redirection with ID {0}".format(item["id"]),
                    **result,
                )

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

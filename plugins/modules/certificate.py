#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2025, Nils Ost (@nils-ost)
# Copyright: (c) 2025, Samuel Assmann <samuel@tecbeat.de>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: certificate

short_description: Manage SSL/TLS certificates in Nginx Proxy Manager

version_added: "1.0.0"

description:
    - Create, query, or delete SSL/TLS certificates in Nginx Proxy Manager.
    - Supports Let's Encrypt certificates with DNS challenge validation.
    - Currently supports the 'domainoffensive' DNS provider for automated certificate generation.
    - For other providers, the module can check if a certificate exists but cannot create new ones.
    - Automatically generates wildcard certificates (domain.example.com and *.domain.example.com).

extends_documentation_fragment:
    - nils_ost.proxymanager.auth

options:
    domain_name:
        description:
            - Primary domain name for the certificate.
            - When creating a certificate, a wildcard certificate is generated
              for both the domain and its wildcard subdomain.
        type: str
        required: true
    provider:
        description:
            - DNS provider for Let's Encrypt DNS-01 challenge.
            - Use domainoffensive to automatically create certificates via the Domain Offensive DNS API.
            - Use other to only check for existing certificates without creating new ones.
        type: str
        required: false
        default: 'other'
        choices: ['domainoffensive', 'other']
    provider_credentials:
        description:
            - API token or credentials for the DNS provider.
            - Required when provider is domainoffensive and state is present.
            - Not required when only checking for existing certificates.
        type: str
        required: false
        default: ''
    state:
        description:
            - Desired state of the certificate.
            - present ensures the certificate exists (creates when provider is domainoffensive).
            - absent ensures the certificate is deleted.
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
"""

EXAMPLES = r"""
- name: Create Let's Encrypt certificate via Domain Offensive
  nils_ost.proxymanager.certificate:
    url: "{{ npm.url }}"
    token: "{{ npm.token }}"
    domain_name: "example.com"
    provider: domainoffensive
    provider_credentials: "{{ domainoffensive_api_token }}"
    state: present
  register: cert
  delegate_to: localhost

- name: Check if certificate exists
  nils_ost.proxymanager.certificate:
    url: "{{ npm.url }}"
    token: "{{ npm.token }}"
    domain_name: "example.com"
    state: present
  register: cert
  delegate_to: localhost

- name: Delete certificate
  nils_ost.proxymanager.certificate:
    url: "{{ npm.url }}"
    token: "{{ npm.token }}"
    domain_name: "example.com"
    state: absent
  delegate_to: localhost
"""

RETURN = r"""
item:
    description:
        - Certificate object from Nginx Proxy Manager.
        - Contains details like certificate ID, domain names, expiry date, etc.
        - Returns null when certificate is deleted or not found.
    type: dict
    returned: when certificate exists or is created
    sample:
        id: 1
        created_on: "2025-01-15 10:30:00"
        modified_on: "2025-01-15 10:30:00"
        provider: "letsencrypt"
        domain_names:
            - "example.com"
            - "*.example.com"
        expires_on: "2025-04-15 10:30:00"
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.nils_ost.proxymanager.plugins.module_utils.client import (
    NginxProxyManagerAPIError,
    NginxProxyManagerAuthError,
    NginxProxyManagerClient,
    NginxProxyManagerError,
    NginxProxyManagerNotFoundError,
    search_by_domain,
)

__all__ = [
    "NginxProxyManagerAPIError",
    "NginxProxyManagerAuthError",
    "NginxProxyManagerClient",
    "NginxProxyManagerError",
    "NginxProxyManagerNotFoundError",
    "search_by_domain",
]


def run_module():
    """
    Execute the certificate module.

    This function handles the main logic for managing SSL/TLS certificates.
    It validates input parameters, manages API communication, and ensures
    idempotent create/update/delete operations.
    """
    module_args = dict(
        url=dict(type="str", required=True),
        token=dict(type="str", required=True, no_log=True),
        domain_name=dict(type="str", required=True),
        provider=dict(
            type="str",
            required=False,
            default="other",
            choices=["domainoffensive", "other"],
        ),
        provider_credentials=dict(type="str", required=False, default="", no_log=True),
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
        if module.params["provider"] == "domainoffensive":
            if not module.params.get("provider_credentials"):
                module.fail_json(
                    msg="provider_credentials is required when using domainoffensive provider",
                    **result,
                )

        client = NginxProxyManagerClient(
            url=module.params["url"],
            token=module.params["token"],
        )

        certificates = client.get("/api/nginx/certificates")
        item = search_by_domain(certificates, module.params["domain_name"])

        if module.params["state"] == "present":
            if item is not None:
                result["item"] = item
                module.exit_json(
                    msg="Certificate already exists with ID {0}".format(item["id"]),
                    **result,
                )

            if module.params["provider"] == "domainoffensive":
                data = dict(
                    domain_names=[
                        module.params["domain_name"],
                        "*.{0}".format(module.params["domain_name"]),
                    ],
                    provider="letsencrypt",
                    meta=dict(
                        dns_challenge=True,
                        dns_provider="domainoffensive",
                        dns_provider_credentials=(
                            "dns_domainoffensive_api_token = {0}".format(
                                module.params["provider_credentials"]
                            )
                        ),
                    ),
                )

                if not module.check_mode:
                    item = client.post("/api/nginx/certificates", data)
                    result["changed"] = True
                    result["item"] = item
                    module.exit_json(
                        msg="Created certificate with ID {0}".format(item["id"]), **result
                    )
                else:
                    result["changed"] = True
                    result["item"] = data
                    module.exit_json(msg="Would have created certificate", **result)

            module.fail_json(
                msg=(
                    "Certificate for domain '{0}' not found and "
                    "provider is set to 'other'. Cannot create certificate.".format(
                        module.params["domain_name"]
                    )
                ),
                **result,
            )

        else:  # state == 'absent'
            if item is None:
                module.exit_json(
                    msg="Certificate already deleted or does not exist", **result
                )

            if not module.check_mode:
                client.delete("/api/nginx/certificates/{0}".format(item["id"]))
                result["changed"] = True
                module.exit_json(
                    msg="Deleted certificate with ID {0}".format(item["id"]), **result
                )
            else:
                result["changed"] = True
                module.exit_json(
                    msg="Would have deleted certificate with ID {0}".format(item["id"]),
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

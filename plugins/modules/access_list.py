#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2025, Samuel Assmann <samuel@tecbeat.de>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: access_list

short_description: Manage Nginx Proxy Manager access lists

version_added: "2.1.0"

description:
    - Create, update, or delete access lists in Nginx Proxy Manager.
    - Access lists combine HTTP Basic authentication entries and IP-based
      allow/deny rules and can be attached to proxy hosts via the
      C(access_list_id) option of the proxy module.
    - The module is idempotent on the access list C(name).

extends_documentation_fragment:
    - nils_ost.proxymanager.auth

options:
    name:
        description:
            - Human-readable name of the access list.
            - Used as the idempotent selector; existing access lists are
              matched on this field.
        required: true
        type: str
    satisfy_any:
        description:
            - If C(true), a client may access the resource if either the
              basic-auth check or the client-IP check succeeds (logical OR).
            - If C(false), both checks must succeed (logical AND).
        required: false
        type: bool
        default: false
    pass_auth:
        description:
            - Whether the Authorization header is passed on to the backend
              after successful basic-auth verification.
        required: false
        type: bool
        default: false
    items:
        description:
            - HTTP Basic authentication entries.
            - Each entry contains a username and password.
        required: false
        type: list
        elements: dict
        default: []
        suboptions:
            username:
                description: Basic-auth username.
                type: str
                required: true
            password:
                description: Basic-auth password (plain text; NPM stores it hashed).
                type: str
                required: true
    clients:
        description:
            - IP-based access rules.
            - Each entry contains a CIDR/IP address and a directive.
        required: false
        type: list
        elements: dict
        default: []
        suboptions:
            address:
                description:
                    - Client IP or CIDR range (for example C(192.168.1.0/24)).
                type: str
                required: true
            directive:
                description:
                    - C(allow) permits the address, C(deny) blocks it.
                type: str
                required: true
                choices: ['allow', 'deny']
    state:
        description:
            - Desired state of the access list.
            - C(present) creates or updates. C(absent) deletes.
        required: false
        type: str
        default: present
        choices: ['absent', 'present']

author:
    - Samuel Assmann (@tecbeat)

notes:
    - Idempotency is based on the C(name) field. Renaming an existing
      access list is therefore not supported by this module; it would be
      treated as a new resource.
    - NPM stores basic-auth passwords hashed. The module cannot detect
      whether a submitted password matches an existing hashed one, so
      C(items) with the same C(username) as an existing entry are always
      re-submitted when present, causing C(changed=true). Provide the
      exact same items list on repeat runs to avoid unnecessary updates,
      or omit C(items) on update runs.

seealso:
    - module: nils_ost.proxymanager.token
    - module: nils_ost.proxymanager.proxy
"""

EXAMPLES = r"""
- name: Create access list with basic auth and IP allowlist
  nils_ost.proxymanager.access_list:
    url: "{{ npm.url }}"
    token: "{{ npm.token }}"
    name: "Internal only"
    satisfy_any: false
    pass_auth: false
    items:
      - username: alice
        password: "{{ alice_password }}"
      - username: bob
        password: "{{ bob_password }}"
    clients:
      - address: 10.0.0.0/8
        directive: allow
      - address: 192.168.0.0/16
        directive: allow
    state: present
  no_log: true

- name: Delete access list
  nils_ost.proxymanager.access_list:
    url: "{{ npm.url }}"
    token: "{{ npm.token }}"
    name: "Internal only"
    state: absent
"""

RETURN = r"""
item:
    description:
        - The access list object as returned by Nginx Proxy Manager.
        - Contains id, name, meta, satisfy_any, pass_auth, proxy_host_count,
          items (with hashed passwords) and clients.
        - Returns C(null) when state is absent or when the list did not exist.
    type: dict
    returned: when state=present
    sample:
        id: 1
        name: "Internal only"
        satisfy_any: false
        pass_auth: false
        proxy_host_count: 0
        items:
            - username: alice
              hint: "a******"
        clients:
            - address: "10.0.0.0/8"
              directive: allow
"""

from ansible.module_utils.basic import AnsibleModule  # noqa: E402

from ansible_collections.nils_ost.proxymanager.plugins.module_utils.client import (
    NginxProxyManagerAPIError,
    NginxProxyManagerClient,
    NginxProxyManagerError,
)

API_ENDPOINT = "/api/nginx/access-lists"


def _find_by_name(items, name):
    """Return the first access list with a matching name, or None."""
    for item in items:
        if item.get("name") == name:
            return item
    return None


def _normalise_items(items):
    """Return a comparable list of ``{username, password}`` dicts."""
    return sorted(
        [
            {
                "username": entry.get("username", ""),
                "password": entry.get("password", ""),
            }
            for entry in items or []
        ],
        key=lambda e: e["username"],
    )


def _normalise_clients(clients):
    """Return a comparable list of ``{address, directive}`` dicts."""
    return sorted(
        [
            {
                "address": entry.get("address", ""),
                "directive": entry.get("directive", ""),
            }
            for entry in clients or []
        ],
        key=lambda e: (e["address"], e["directive"]),
    )


def _matches_existing(existing, desired):
    """
    Compare a desired access-list payload with what NPM returned for the
    existing resource. Returns True if nothing has to change.
    """
    if existing.get("name") != desired["name"]:
        return False
    if bool(existing.get("satisfy_any")) != bool(desired["satisfy_any"]):
        return False
    if bool(existing.get("pass_auth")) != bool(desired["pass_auth"]):
        return False

    if _normalise_clients(existing.get("clients")) != _normalise_clients(
        desired["clients"]
    ):
        return False

    desired_usernames = sorted(
        entry["username"] for entry in desired["items"] if entry.get("username")
    )
    existing_usernames = sorted(
        entry.get("username", "") for entry in existing.get("items") or []
    )
    if desired_usernames != existing_usernames:
        return False

    if any(entry.get("password") for entry in desired["items"]):
        return False

    return True


def run_module():
    module_args = dict(
        url=dict(type="str", required=True),
        token=dict(type="str", required=True, no_log=True),
        name=dict(type="str", required=True),
        satisfy_any=dict(type="bool", required=False, default=False),
        pass_auth=dict(type="bool", required=False, default=False),
        items=dict(
            type="list",
            elements="dict",
            required=False,
            default=[],
            no_log=True,
            options=dict(
                username=dict(type="str", required=True),
                password=dict(type="str", required=True, no_log=True),
            ),
        ),
        clients=dict(
            type="list",
            elements="dict",
            required=False,
            default=[],
            options=dict(
                address=dict(type="str", required=True),
                directive=dict(
                    type="str", required=True, choices=["allow", "deny"]
                ),
            ),
        ),
        state=dict(type="str", default="present", choices=["absent", "present"]),
    )

    result = dict(changed=False, item=None)
    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    try:
        client = NginxProxyManagerClient(module.params["url"], module.params["token"])

        existing_list = client.get(
            "{0}?expand=items,clients".format(API_ENDPOINT)
        )
        existing = _find_by_name(existing_list, module.params["name"])

        if module.params["state"] == "absent":
            if existing is None:
                module.exit_json(msg="Access list already absent", **result)
            if not module.check_mode:
                client.delete("{0}/{1}".format(API_ENDPOINT, existing["id"]))
            result["changed"] = True
            module.exit_json(msg="Deleted access list", **result)

        # state == present
        desired = dict(
            name=module.params["name"],
            satisfy_any=module.params["satisfy_any"],
            pass_auth=module.params["pass_auth"],
            items=module.params["items"] or [],
            clients=module.params["clients"] or [],
        )

        if existing is None:
            if module.check_mode:
                result["changed"] = True
                result["item"] = desired
                module.exit_json(msg="Would have created access list", **result)
            item = client.post(API_ENDPOINT, desired)
            result["changed"] = True
            result["item"] = item
            module.exit_json(
                msg="Created access list {0}".format(item["id"]), **result
            )

        if _matches_existing(existing, desired):
            result["item"] = existing
            module.exit_json(
                msg="Access list already configured (id={0})".format(existing["id"]),
                **result,
            )

        if module.check_mode:
            result["changed"] = True
            result["item"] = desired
            module.exit_json(msg="Would have updated access list", **result)

        item = client.put(
            "{0}/{1}".format(API_ENDPOINT, existing["id"]), desired
        )
        result["changed"] = True
        result["item"] = item
        module.exit_json(
            msg="Updated access list {0}".format(item["id"]), **result
        )

    except NginxProxyManagerAPIError as exc:
        error_msg = "API error: {0} (HTTP {1})".format(exc, exc.status_code)
        if exc.response_text:
            error_msg += " - {0}".format(exc.response_text)
        module.fail_json(msg=error_msg, **result)
    except NginxProxyManagerError as exc:
        module.fail_json(
            msg="Nginx Proxy Manager error: {0}".format(exc), **result
        )


def main():
    run_module()


if __name__ == "__main__":
    main()

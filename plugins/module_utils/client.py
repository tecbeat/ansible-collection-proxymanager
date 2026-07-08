# -*- coding: utf-8 -*-

# Copyright: (c) 2025, Nils Ost (@nils-ost)
# Copyright: (c) 2025, Samuel Assmann <samuel@tecbeat.de>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""HTTP client for the Nginx Proxy Manager REST API.

This module_util is the shared foundation used by every module in the
``nils_ost.proxymanager`` collection. It provides:

* :class:`NginxProxyManagerClient` -- a thin wrapper around
  ``requests.Session`` that handles auth headers and turns HTTP errors
  into typed exceptions.
* An exception hierarchy: :class:`NginxProxyManagerError` (base),
  :class:`NginxProxyManagerAuthError`,
  :class:`NginxProxyManagerNotFoundError`,
  :class:`NginxProxyManagerAPIError`.
* :func:`authenticate` -- one-shot helper that exchanges user credentials
  for a bearer token via ``POST /api/tokens``.
* :func:`compare_dicts` and :func:`search_by_domain` -- small helpers
  used across CRUD-style modules to keep them idempotent.

Modules in this collection import from here via the FQCN::

    from ansible_collections.nils_ost.proxymanager.plugins.module_utils.client import (
        NginxProxyManagerClient,
        authenticate,
    )

Third-party collections may use the same import path.
"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

try:
    import requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class NginxProxyManagerError(Exception):
    """Base exception for Nginx Proxy Manager operations."""


class NginxProxyManagerAuthError(NginxProxyManagerError):
    """Authentication error when talking to the Nginx Proxy Manager API."""


class NginxProxyManagerAPIError(NginxProxyManagerError):
    """Generic API error when talking to the Nginx Proxy Manager API."""

    def __init__(self, message, status_code=None, response_text=None):
        self.status_code = status_code
        self.response_text = response_text
        super(NginxProxyManagerAPIError, self).__init__(message)


class NginxProxyManagerNotFoundError(NginxProxyManagerError):
    """Raised when a requested resource is not found (HTTP 404)."""


# ---------------------------------------------------------------------------
# HTTP client
# ---------------------------------------------------------------------------

class NginxProxyManagerClient:
    """
    Thin wrapper around ``requests.Session`` for the Nginx Proxy Manager
    REST API.

    The client holds a bearer token, prefixes every request with the base
    URL, and translates HTTP status codes into the collection's exception
    hierarchy.
    """

    def __init__(self, url, token):
        if not HAS_REQUESTS:
            raise ImportError("The 'requests' library is required for this module")

        self.url = url.rstrip("/")
        self.token = token
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": "Bearer {0}".format(token),
                "Content-Type": "application/json",
            }
        )

    def _handle_response(self, response, expected_status):
        """
        Return the JSON payload for expected status codes, raise a typed
        exception otherwise.
        """
        if isinstance(expected_status, int):
            expected_status = [expected_status]

        if response.status_code in expected_status:
            # DELETE returns boolean true instead of JSON
            if response.status_code == 200 and not response.text:
                return True
            try:
                return response.json()
            except ValueError:
                return response.text

        if response.status_code == 401:
            raise NginxProxyManagerAuthError(
                "Authentication failed. Invalid or expired token."
            )
        if response.status_code == 404:
            raise NginxProxyManagerNotFoundError(
                "Resource not found: {0}".format(response.text)
            )
        raise NginxProxyManagerAPIError(
            "API request failed with status {0}".format(response.status_code),
            status_code=response.status_code,
            response_text=response.text,
        )

    def get(self, endpoint, expected_status=200):
        response = self.session.get("{0}{1}".format(self.url, endpoint))
        return self._handle_response(response, expected_status)

    def post(self, endpoint, data, expected_status=201):
        response = self.session.post(
            "{0}{1}".format(self.url, endpoint), json=data
        )
        return self._handle_response(response, expected_status)

    def put(self, endpoint, data, expected_status=200):
        response = self.session.put(
            "{0}{1}".format(self.url, endpoint), json=data
        )
        return self._handle_response(response, expected_status)

    def delete(self, endpoint, expected_status=200):
        response = self.session.delete("{0}{1}".format(self.url, endpoint))
        return self._handle_response(response, expected_status)


# ---------------------------------------------------------------------------
# Authentication helper
# ---------------------------------------------------------------------------

def authenticate(url, user, password):
    """
    Obtain a bearer token from ``/api/tokens``.

    Args:
        url: Base URL of the Nginx Proxy Manager instance (with or without
            trailing slash).
        user: Identity (typically the admin email).
        password: Secret for the identity.

    Returns:
        tuple: ``(normalised_url, token)``. ``normalised_url`` has any
        trailing slash stripped so it can be passed straight to
        :class:`NginxProxyManagerClient`.

    Raises:
        ImportError: If the ``requests`` library is not installed.
        NginxProxyManagerAuthError: On credential failure or malformed
            response.
        NginxProxyManagerAPIError: On any other non-200 response.
    """
    if not HAS_REQUESTS:
        raise ImportError("The 'requests' library is required for this module")

    normalised_url = url.rstrip("/")
    try:
        response = requests.post(
            "{0}/api/tokens".format(normalised_url),
            json={"identity": user, "secret": password},
            headers={"Content-Type": "application/json"},
        )
    except requests.exceptions.RequestException as exc:
        raise NginxProxyManagerAPIError(
            "Connection error: {0}".format(exc)
        )

    if response.status_code != 200:
        raise NginxProxyManagerAuthError(
            "Authentication failed: {0}".format(response.text)
        )

    try:
        payload = response.json()
    except ValueError:
        raise NginxProxyManagerAuthError(
            "API response is not valid JSON: {0}".format(response.text)
        )

    if "token" not in payload:
        raise NginxProxyManagerAuthError(
            "API response does not contain a token"
        )

    return normalised_url, payload["token"]


# ---------------------------------------------------------------------------
# Common helpers used by more than one module
# ---------------------------------------------------------------------------

def compare_dicts(dict1, dict2, keys):
    """
    Compare two dictionaries on a fixed set of keys.

    Returns ``True`` when every key exists in both dicts and has the same
    value. Missing keys count as a mismatch.
    """
    for key in keys:
        if key not in dict1 or key not in dict2:
            return False
        if dict1.get(key) != dict2.get(key):
            return False
    return True


def search_by_domain(items, domain_name):
    """
    Return the first item in ``items`` whose ``domain_names`` list contains
    ``domain_name``, or ``None`` if there is no match.
    """
    for item in items:
        if domain_name in item.get("domain_names", []):
            return item
    return None

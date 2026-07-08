# -*- coding: utf-8 -*-

# Copyright: (c) 2025, Nils Ost (@nils-ost)
# Copyright: (c) 2025, Samuel Assmann <samuel@tecbeat.de>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Shared authentication documentation fragment.

Every task-level module in the ``nils_ost.proxymanager`` collection
speaks to the same Nginx Proxy Manager instance and needs the same two
options: the base ``url`` and a bearer ``token``. This fragment holds
those two option definitions in one place so they stay consistent across
modules.

Modules pull the fragment in with::

    extends_documentation_fragment:
        - nils_ost.proxymanager.auth
"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type


class ModuleDocFragment(object):
    """Shared authentication options: ``url`` and ``token``."""

    DOCUMENTATION = r"""
options:
    url:
        description:
            - Base URL of the Nginx Proxy Manager instance, including the
              scheme and admin port (for example ``https://npm.example.com``).
            - Trailing slashes are stripped automatically.
        required: true
        type: str
    token:
        description:
            - Bearer token used to authenticate against the Nginx Proxy
              Manager REST API.
            - Obtain this token from the nils_ost.proxymanager.token
              module and pass it here.
        required: true
        type: str
"""

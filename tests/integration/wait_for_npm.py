"""Block until NPM accepts the configured admin credentials at /api/tokens.

A 200 response proves the database is migrated and the INITIAL_ADMIN_* user
has been created. Configuration via environment variables:

    NPM_HOST            (default: localhost)
    NPM_PORT            (default: 81)
    NPM_ADMIN_EMAIL     (default: admin@example.com)
    NPM_ADMIN_PASSWORD  (default: changeme)
    NPM_WAIT_TIMEOUT    seconds, total wait budget (default: 180)
    NPM_WAIT_INTERVAL   seconds between attempts  (default: 2)
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request


def wait_for_login(
    url: str,
    identity: str,
    secret: str,
    timeout: float,
    interval: float,
) -> None:
    body = json.dumps({"identity": identity, "secret": secret}).encode()
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    deadline = time.monotonic() + timeout
    attempt = 0
    last_reason = "no attempts made"
    while time.monotonic() < deadline:
        attempt += 1
        try:
            with urllib.request.urlopen(request, timeout=interval) as response:
                if response.status == 200:
                    print(f"NPM ready after {attempt} attempt(s).")
                    return
                last_reason = f"HTTP {response.status}"
        except urllib.error.HTTPError as exc:
            last_reason = f"HTTP {exc.code}"
        except urllib.error.URLError as exc:
            last_reason = f"URLError: {exc.reason}"
        except (ConnectionError, TimeoutError) as exc:
            last_reason = f"{type(exc).__name__}: {exc}"
        if attempt == 1 or attempt % 10 == 0:
            print(f"  attempt {attempt}: {last_reason}")
        time.sleep(interval)
    raise TimeoutError(
        f"NPM did not become ready within {timeout:.0f}s "
        f"(last reason: {last_reason})"
    )


def main() -> int:
    host = os.environ.get("NPM_HOST", "localhost")
    port = os.environ.get("NPM_PORT", "81")
    identity = os.environ.get("NPM_ADMIN_EMAIL", "admin@example.com")
    secret = os.environ.get("NPM_ADMIN_PASSWORD", "changeme")
    timeout = float(os.environ.get("NPM_WAIT_TIMEOUT", "180"))
    interval = float(os.environ.get("NPM_WAIT_INTERVAL", "2"))

    url = f"http://{host}:{port}/api/tokens"
    print(f"Waiting for NPM admin login at {url} (timeout {timeout:.0f}s)...")
    try:
        wait_for_login(url, identity, secret, timeout, interval)
    except TimeoutError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

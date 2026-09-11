"""Package SemVer and HTTP API version constants.

Two independent version axes:

- ``PACKAGE_VERSION`` — Python distribution / deployable product (SemVer).
- ``API_VERSION`` — HTTP contract consumed by mobile and other clients.

Mobile clients depend on the HTTP API version, not on the pip package.
"""

from __future__ import annotations

PACKAGE_VERSION = "0.2.0"
API_VERSION = "v1"
API_PREFIX = f"/api/{API_VERSION}"

__all__ = ["API_PREFIX", "API_VERSION", "PACKAGE_VERSION"]

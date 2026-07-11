"""Deterministic site identifier, derived from location.

No user auth in the demo scope (Section 6 of the dev plan), so a site is
identified by its coordinates (rounded to ~100m) rather than by an account.
Two requests for the same rounded lat/lon share logged production and a
calibration bias factor.
"""

import hashlib


def site_id_for(latitude: float, longitude: float) -> str:
    """Derive a short, stable site ID from rounded coordinates."""
    key = f"{round(latitude, 3)},{round(longitude, 3)}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]

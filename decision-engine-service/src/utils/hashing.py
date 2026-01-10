"""
Hashing utilities for Idea Registry.

Computes canonical_hash (SHA256) for idea deduplication
and avatar_hash (MD5) for avatar deduplication.

Port of JavaScript implementation from n8n idea_registry_create workflow.
"""

import hashlib
import json
from typing import Optional


# Canonical fields for idea hash - must match JS implementation exactly
CANONICAL_FIELDS = [
    "angle_type",
    "core_belief",
    "promise_type",
    "emotion_primary",
    "emotion_intensity",
    "message_structure",
    "opening_type",
    "state_before",
    "state_after",
    "context_frame",
    "source_type",
    "risk_level",
    "horizon",
    "schema_version",
]


def compute_canonical_hash(payload: dict) -> str:
    """
    Compute SHA256 hash for idea deduplication.

    Port of JavaScript implementation:
    ```js
    const canonicalFields = ['angle_type', 'core_belief', ...];
    const canonicalData = {};
    for (const field of canonicalFields) {
      if (payload[field] !== undefined) {
        canonicalData[field] = payload[field];
      }
    }
    const sortedKeys = Object.keys(canonicalData).sort();
    const sortedData = {};
    for (const key of sortedKeys) {
      sortedData[key] = canonicalData[key];
    }
    const jsonString = JSON.stringify(sortedData);
    crypto.createHash('sha256').update(jsonString).digest('hex');
    ```

    Args:
        payload: Decomposed creative payload with canonical fields

    Returns:
        64-character SHA256 hex string
    """
    # Extract only canonical fields that are defined (not None, not missing)
    # In JS: payload[field] !== undefined
    canonical_data = {}
    for field in CANONICAL_FIELDS:
        if field in payload and payload[field] is not None:
            canonical_data[field] = payload[field]

    # Sort keys alphabetically (matches JS Object.keys().sort())
    sorted_data = {k: canonical_data[k] for k in sorted(canonical_data.keys())}

    # JSON stringify with same format as JS
    # JSON.stringify in JS uses no spaces, Python default is the same
    json_string = json.dumps(sorted_data, separators=(",", ":"))

    # SHA256 hash
    return hashlib.sha256(json_string.encode("utf-8")).hexdigest()


def compute_avatar_hash(
    vertical: Optional[str],
    geo: Optional[str],
    deep_desire_type: Optional[str],
    primary_trigger: Optional[str],
    awareness_level: Optional[str],
) -> Optional[str]:
    """
    Compute MD5 hash for avatar deduplication.

    Port of JavaScript implementation (Issue #194: includes geo):
    ```js
    if (deepDesireType && primaryTrigger && awarenessLevel) {
      const avatarHashInput = [
        vertical,
        geo,
        deepDesireType,
        primaryTrigger,
        awarenessLevel
      ].join('|');
      avatarCanonicalHash = crypto.createHash('md5').update(avatarHashInput).digest('hex');
    }
    ```

    Args:
        vertical: Buyer vertical (e.g., 'nutra', 'crypto')
        geo: Buyer geo (e.g., 'RU', 'KZ') - included in hash for geo-specific avatars
        deep_desire_type: Avatar deep desire type
        primary_trigger: Avatar primary trigger
        awareness_level: Avatar awareness level

    Returns:
        32-character MD5 hex string, or None if required fields are missing/empty
    """
    # Match JS truthiness check: if (deepDesireType && primaryTrigger && awarenessLevel)
    # In JS, empty string is falsy, so we check for truthy values
    if not deep_desire_type or not primary_trigger or not awareness_level:
        return None

    # Build hash input: "vertical|geo|deep_desire_type|primary_trigger|awareness_level"
    # Note: vertical and geo can be 'unknown' (default from JS), but we still include them
    avatar_hash_input = f"{vertical or 'unknown'}|{geo or 'unknown'}|{deep_desire_type}|{primary_trigger}|{awareness_level}"

    # MD5 hash
    return hashlib.md5(avatar_hash_input.encode("utf-8")).hexdigest()

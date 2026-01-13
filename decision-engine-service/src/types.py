"""
Type definitions for GenomAI Decision Engine.

Issue: #597 (Epic: #596)
"""

from enum import Enum
from typing import Literal


class ModuleType(str, Enum):
    """
    Module types for module_bank.

    7 independent variables from VISION.md:
    - hook_mechanism: How the creative captures attention
    - angle_type: The approach/perspective used
    - message_structure: How the message is organized
    - ump_type: Unique mechanism of promise
    - promise_type: Type of promise made
    - proof_type: Type of proof/evidence used
    - cta_style: Call-to-action style
    """

    HOOK_MECHANISM = "hook_mechanism"
    ANGLE_TYPE = "angle_type"
    MESSAGE_STRUCTURE = "message_structure"
    UMP_TYPE = "ump_type"
    PROMISE_TYPE = "promise_type"
    PROOF_TYPE = "proof_type"
    CTA_STYLE = "cta_style"


# Type alias for module_type values
ModuleTypeLiteral = Literal[
    "hook_mechanism",
    "angle_type",
    "message_structure",
    "ump_type",
    "promise_type",
    "proof_type",
    "cta_style",
]

# List of all module types for iteration
MODULE_TYPES: list[str] = [t.value for t in ModuleType]


# Legacy types (backward compatibility, remove after #598)
class LegacyModuleType(str, Enum):
    """Legacy module types. Will be removed after #598 data migration."""

    HOOK = "hook"
    PROMISE = "promise"
    PROOF = "proof"


# Mapping from legacy to new types (for #598 data migration)
LEGACY_TO_NEW_TYPE_MAP: dict[str, str] = {
    "hook": "hook_mechanism",
    "promise": "promise_type",
    "proof": "proof_type",
}

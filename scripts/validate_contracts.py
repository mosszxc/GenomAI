#!/usr/bin/env python3
"""
Contract Validation Script

Validates that workflow contracts are compatible:
- Producer output schema must satisfy consumer input schema
- All required fields in input must be present in output

Usage:
    python scripts/validate_contracts.py
    python scripts/validate_contracts.py --verbose
    python scripts/validate_contracts.py --check-pair idea_registry_output decision_engine_input

Exit codes:
    0 - All contracts valid
    1 - Contract validation errors found
"""

import json
import sys
from pathlib import Path
from typing import Any

CONTRACTS_DIR = Path(__file__).parent.parent / "infrastructure" / "contracts"

# Define producer -> consumer relationships
CONTRACT_PAIRS = [
    ("idea_registry_output", "decision_engine_input"),
    ("decision_engine_output", "hypothesis_factory_input"),
    ("learning_loop_input", None),  # Terminal - no downstream consumer
    ("learning_loop_output", None),  # Terminal - response only
]


def load_contract(name: str) -> dict:
    """Load a contract JSON file."""
    path = CONTRACTS_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Contract not found: {path}")

    with open(path) as f:
        return json.load(f)


def get_required_fields(schema: dict) -> set:
    """Extract required fields from a JSON schema."""
    required = set(schema.get("required", []))
    return required


def get_property_types(schema: dict) -> dict:
    """Extract property types from a JSON schema."""
    properties = schema.get("properties", {})
    types = {}

    for name, prop in properties.items():
        if "type" in prop:
            prop_type = prop["type"]
            if isinstance(prop_type, list):
                types[name] = set(prop_type)
            else:
                types[name] = {prop_type}
        elif "$ref" in prop:
            types[name] = {"object"}  # Assume refs are objects
        else:
            types[name] = {"any"}

    return types


def validate_contract_pair(
    producer_name: str, consumer_name: str, verbose: bool = False
) -> list[str]:
    """
    Validate that producer output satisfies consumer input requirements.

    Returns list of validation errors.
    """
    errors = []

    try:
        producer = load_contract(producer_name)
        consumer = load_contract(consumer_name)
    except FileNotFoundError as e:
        return [str(e)]

    producer_props = get_property_types(producer)
    consumer_required = get_required_fields(consumer)
    consumer_props = get_property_types(consumer)

    if verbose:
        print(f"\n  Producer '{producer_name}':")
        print(f"    Properties: {list(producer_props.keys())}")
        print(f"  Consumer '{consumer_name}':")
        print(f"    Required: {consumer_required}")
        print(f"    Properties: {list(consumer_props.keys())}")

    # Check all required consumer fields exist in producer output
    for field in consumer_required:
        if field not in producer_props:
            errors.append(
                f"Missing required field: '{field}' required by {consumer_name} "
                f"but not in {producer_name} output"
            )

    # Check type compatibility for common fields
    for field in producer_props.keys() & consumer_props.keys():
        producer_types = producer_props[field]
        consumer_types = consumer_props[field]

        # Types are compatible if they have any overlap
        if not (producer_types & consumer_types) and "any" not in producer_types:
            # Allow null in producer if consumer accepts null
            if "null" in producer_types and "null" in consumer_types:
                continue
            errors.append(
                f"Type mismatch for '{field}': "
                f"{producer_name} outputs {producer_types}, "
                f"{consumer_name} expects {consumer_types}"
            )

    return errors


def validate_all_contracts(verbose: bool = False) -> dict[str, list[str]]:
    """Validate all contract pairs."""
    all_errors = {}

    for producer, consumer in CONTRACT_PAIRS:
        if consumer is None:
            if verbose:
                print(f"\n[SKIP] {producer} (terminal - no consumer)")
            continue

        pair_name = f"{producer} -> {consumer}"
        if verbose:
            print(f"\n[CHECK] {pair_name}")

        errors = validate_contract_pair(producer, consumer, verbose)
        if errors:
            all_errors[pair_name] = errors

    return all_errors


def check_contracts_exist() -> list[str]:
    """Check that all referenced contracts exist."""
    missing = []

    for producer, consumer in CONTRACT_PAIRS:
        producer_path = CONTRACTS_DIR / f"{producer}.json"
        if not producer_path.exists():
            missing.append(str(producer_path))

        if consumer:
            consumer_path = CONTRACTS_DIR / f"{consumer}.json"
            if not consumer_path.exists():
                missing.append(str(consumer_path))

    return missing


def main():
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    print("=" * 60)
    print("GenomAI Contract Validation")
    print("=" * 60)

    # Check contracts directory exists
    if not CONTRACTS_DIR.exists():
        print(f"\n[ERROR] Contracts directory not found: {CONTRACTS_DIR}")
        sys.exit(1)

    print(f"\nContracts directory: {CONTRACTS_DIR}")

    # List available contracts
    contracts = list(CONTRACTS_DIR.glob("*.json"))
    print(f"Found {len(contracts)} contract files:")
    for c in sorted(contracts):
        print(f"  - {c.name}")

    # Check for missing contracts
    missing = check_contracts_exist()
    if missing:
        print(f"\n[ERROR] Missing contracts:")
        for m in missing:
            print(f"  - {m}")
        sys.exit(1)

    # Check specific pair if requested
    if "--check-pair" in sys.argv:
        idx = sys.argv.index("--check-pair")
        if idx + 2 >= len(sys.argv):
            print("\n[ERROR] --check-pair requires two arguments: producer consumer")
            sys.exit(1)

        producer = sys.argv[idx + 1]
        consumer = sys.argv[idx + 2]

        print(f"\nValidating pair: {producer} -> {consumer}")
        errors = validate_contract_pair(producer, consumer, verbose=True)

        if errors:
            print(f"\n[FAIL] {len(errors)} error(s) found:")
            for e in errors:
                print(f"  - {e}")
            sys.exit(1)
        else:
            print("\n[PASS] Contracts are compatible")
            sys.exit(0)

    # Validate all pairs
    print("\n" + "-" * 60)
    print("Validating contract pairs...")

    all_errors = validate_all_contracts(verbose)

    print("\n" + "=" * 60)

    if all_errors:
        print("VALIDATION FAILED")
        print("=" * 60)

        total_errors = sum(len(e) for e in all_errors.values())
        print(f"\n{total_errors} error(s) in {len(all_errors)} pair(s):\n")

        for pair, errors in all_errors.items():
            print(f"\n[FAIL] {pair}")
            for e in errors:
                print(f"       - {e}")

        sys.exit(1)
    else:
        print("VALIDATION PASSED")
        print("=" * 60)
        print(
            f"\nAll {len([p for p, c in CONTRACT_PAIRS if c])} contract pairs are compatible"
        )
        sys.exit(0)


if __name__ == "__main__":
    main()

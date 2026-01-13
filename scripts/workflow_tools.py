#!/usr/bin/env python3
"""
Batch workflow editing tools for n8n JSON files.
Reduces token usage by enabling single-operation batch edits.

Usage:
    python workflow_tools.py shift_nodes workflow.json --after-x 2660 --delta 220
    python workflow_tools.py update_connections workflow.json --from "Check Unique" --to "Process Data"
    python workflow_tools.py validate workflow.json
"""

import json
import argparse
import sys
from pathlib import Path
from typing import Optional


def load_workflow(path: str) -> dict:
    """Load n8n workflow JSON."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_workflow(workflow: dict, path: str) -> None:
    """Save n8n workflow JSON with proper formatting."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(workflow, f, indent=2, ensure_ascii=False)
    print(f"Saved: {path}")


def shift_nodes(
    workflow: dict, after_x: int, delta: int, after_y: Optional[int] = None
) -> dict:
    """
    Shift all nodes with position[0] > after_x by delta pixels.
    Optionally filter by Y position.

    Example: shift_nodes(wf, after_x=2660, delta=220)
    Shifts all nodes right of x=2660 by 220 pixels.
    """
    nodes_shifted = 0
    for node in workflow.get("nodes", []):
        pos = node.get("position", [0, 0])
        if pos[0] > after_x:
            if after_y is None or pos[1] == after_y:
                node["position"][0] += delta
                nodes_shifted += 1
                print(
                    f"  Shifted: {node['name']} -> [{node['position'][0]}, {node['position'][1]}]"
                )

    print(f"Total shifted: {nodes_shifted} nodes")
    return workflow


def shift_nodes_by_name(
    workflow: dict, node_names: list[str], delta_x: int, delta_y: int = 0
) -> dict:
    """
    Shift specific nodes by name.

    Example: shift_nodes_by_name(wf, ["Insert Premise", "Track Created"], delta_x=220)
    """
    for node in workflow.get("nodes", []):
        if node["name"] in node_names:
            node["position"][0] += delta_x
            node["position"][1] += delta_y
            print(
                f"  Shifted: {node['name']} -> [{node['position'][0]}, {node['position'][1]}]"
            )

    return workflow


def update_connection(
    workflow: dict,
    from_node: str,
    to_node: str,
    output_index: int = 0,
    input_index: int = 0,
) -> dict:
    """
    Update or create a connection between nodes.

    Example: update_connection(wf, "Check Unique", "Process Data")
    """
    connections = workflow.get("connections", {})

    if from_node not in connections:
        connections[from_node] = {"main": [[]]}

    main = connections[from_node].get("main", [[]])
    while len(main) <= output_index:
        main.append([])

    # Remove existing connection to target
    main[output_index] = [c for c in main[output_index] if c.get("node") != to_node]

    # Add new connection
    main[output_index].append({"node": to_node, "type": "main", "index": input_index})

    connections[from_node]["main"] = main
    workflow["connections"] = connections

    print(f"Connected: {from_node}[{output_index}] -> {to_node}[{input_index}]")
    return workflow


def remove_connection(workflow: dict, from_node: str, to_node: str) -> dict:
    """Remove connection between nodes."""
    connections = workflow.get("connections", {})

    if from_node in connections:
        for output in connections[from_node].get("main", []):
            connections[from_node]["main"] = [
                [c for c in output if c.get("node") != to_node]
                for output in connections[from_node]["main"]
            ]

    print(f"Removed connection: {from_node} -> {to_node}")
    return workflow


def insert_node_between(
    workflow: dict, new_node: dict, before_node: str, after_node: str
) -> dict:
    """
    Insert a new node between two existing nodes.
    Updates connections automatically.
    """
    # Add node
    workflow["nodes"].append(new_node)
    print(f"Added node: {new_node['name']}")

    # Update connections
    workflow = remove_connection(workflow, before_node, after_node)
    workflow = update_connection(workflow, before_node, new_node["name"])
    workflow = update_connection(workflow, new_node["name"], after_node)

    return workflow


def validate_workflow(workflow: dict) -> list[str]:
    """
    Basic validation of workflow structure.
    Returns list of issues found.
    """
    issues = []

    # Check nodes exist
    nodes = workflow.get("nodes", [])
    if not nodes:
        issues.append("No nodes found in workflow")
        return issues

    node_names = {n["name"] for n in nodes}
    connections = workflow.get("connections", {})

    # Check all connections reference valid nodes
    for from_node, conn in connections.items():
        if from_node not in node_names:
            issues.append(f"Connection from unknown node: {from_node}")

        for output in conn.get("main", []):
            for c in output:
                to_node = c.get("node")
                if to_node and to_node not in node_names:
                    issues.append(f"Connection to unknown node: {to_node}")

    # Check for duplicate node names
    if len(node_names) != len(nodes):
        issues.append("Duplicate node names found")

    # Check node positions
    for node in nodes:
        pos = node.get("position", [])
        if len(pos) != 2:
            issues.append(f"Invalid position for node: {node['name']}")

    if issues:
        print("Validation FAILED:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("Validation PASSED")

    return issues


def list_nodes(workflow: dict) -> None:
    """Print all nodes with their positions."""
    print("\nNodes:")
    print("-" * 60)
    for node in sorted(
        workflow.get("nodes", []), key=lambda n: n.get("position", [0, 0])[0]
    ):
        pos = node.get("position", [0, 0])
        print(f"  [{pos[0]:4}, {pos[1]:4}] {node['name']}")


def main():
    parser = argparse.ArgumentParser(description="Batch workflow editing tools")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # shift_nodes command
    shift_parser = subparsers.add_parser(
        "shift_nodes", help="Shift nodes by X position"
    )
    shift_parser.add_argument("workflow", help="Workflow JSON file")
    shift_parser.add_argument(
        "--after-x", type=int, required=True, help="Shift nodes after this X"
    )
    shift_parser.add_argument("--delta", type=int, required=True, help="Shift amount")
    shift_parser.add_argument("--after-y", type=int, help="Optional Y filter")
    shift_parser.add_argument(
        "--dry-run", action="store_true", help="Preview without saving"
    )

    # shift_by_name command
    name_parser = subparsers.add_parser("shift_by_name", help="Shift specific nodes")
    name_parser.add_argument("workflow", help="Workflow JSON file")
    name_parser.add_argument(
        "--nodes", nargs="+", required=True, help="Node names to shift"
    )
    name_parser.add_argument("--delta-x", type=int, default=0, help="X shift")
    name_parser.add_argument("--delta-y", type=int, default=0, help="Y shift")
    name_parser.add_argument(
        "--dry-run", action="store_true", help="Preview without saving"
    )

    # validate command
    val_parser = subparsers.add_parser("validate", help="Validate workflow")
    val_parser.add_argument("workflow", help="Workflow JSON file")

    # list command
    list_parser = subparsers.add_parser("list", help="List all nodes")
    list_parser.add_argument("workflow", help="Workflow JSON file")

    # connect command
    conn_parser = subparsers.add_parser("connect", help="Update connection")
    conn_parser.add_argument("workflow", help="Workflow JSON file")
    conn_parser.add_argument(
        "--from", dest="from_node", required=True, help="Source node"
    )
    conn_parser.add_argument("--to", dest="to_node", required=True, help="Target node")
    conn_parser.add_argument(
        "--dry-run", action="store_true", help="Preview without saving"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    workflow = load_workflow(args.workflow)

    if args.command == "shift_nodes":
        workflow = shift_nodes(workflow, args.after_x, args.delta, args.after_y)
        if not args.dry_run:
            save_workflow(workflow, args.workflow)

    elif args.command == "shift_by_name":
        workflow = shift_nodes_by_name(workflow, args.nodes, args.delta_x, args.delta_y)
        if not args.dry_run:
            save_workflow(workflow, args.workflow)

    elif args.command == "validate":
        issues = validate_workflow(workflow)
        sys.exit(1 if issues else 0)

    elif args.command == "list":
        list_nodes(workflow)

    elif args.command == "connect":
        workflow = update_connection(workflow, args.from_node, args.to_node)
        if not args.dry_run:
            save_workflow(workflow, args.workflow)


if __name__ == "__main__":
    main()

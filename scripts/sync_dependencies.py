#!/usr/bin/env python3
"""
Sync Dependencies Script

Extracts workflow dependencies from n8n API and updates:
1. infrastructure/schemas/dependency_manifest.json
2. docs/DEPENDENCY_GRAPH.md (Mermaid diagram)

Usage:
    python scripts/sync_dependencies.py
    python scripts/sync_dependencies.py --dry-run
    python scripts/sync_dependencies.py --verbose

Environment:
    N8N_API_URL: n8n API base URL
    N8N_API_KEY: n8n API key

Exit codes:
    0 - Success
    1 - Error
"""

import os
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
import urllib.request
import urllib.error

# Configuration
N8N_API_URL = os.getenv("N8N_API_URL", "https://kazamaqwe.app.n8n.cloud/api/v1")
N8N_API_KEY = os.getenv("N8N_API_KEY", "")

PROJECT_ROOT = Path(__file__).parent.parent
MANIFEST_PATH = PROJECT_ROOT / "infrastructure" / "schemas" / "dependency_manifest.json"
GRAPH_PATH = PROJECT_ROOT / "docs" / "DEPENDENCY_GRAPH.md"


def api_request(endpoint: str) -> dict:
    """Make authenticated request to n8n API."""
    url = f"{N8N_API_URL}/{endpoint}"
    headers = {
        "X-N8N-API-KEY": N8N_API_KEY,
        "Accept": "application/json",
    }

    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        print(f"API Error: {e.code} - {e.reason}")
        raise
    except urllib.error.URLError as e:
        print(f"Connection Error: {e.reason}")
        raise


def extract_webhook_calls(nodes: list) -> list[str]:
    """Extract workflow names from httpRequest nodes calling webhooks."""
    calls = []

    for node in nodes:
        if node.get("type") != "n8n-nodes-base.httpRequest":
            continue

        params = node.get("parameters", {})
        url = params.get("url", "")

        # Skip if url is not a string (can be dict in n8n expressions)
        if not isinstance(url, str):
            continue

        # Extract webhook path
        if "/webhook/" in url:
            # Pattern: /webhook/workflow-name or /webhook-test/workflow-name
            match = re.search(r"/webhook(?:-test)?/([a-zA-Z0-9_-]+)", url)
            if match:
                calls.append(match.group(1))

    return list(set(calls))


def extract_supabase_tables(nodes: list) -> tuple[list[str], list[str]]:
    """Extract tables read/written by Supabase nodes."""
    reads = []
    writes = []

    for node in nodes:
        node_type = node.get("type", "")

        # Supabase node
        if "supabase" in node_type.lower():
            params = node.get("parameters", {})
            table = params.get("tableId", params.get("table", ""))
            operation = params.get("operation", "")

            # Skip if table is not a string (can be dict in n8n expressions)
            if not isinstance(table, str):
                continue

            if table:
                if operation in ["create", "update", "upsert", "delete"]:
                    writes.append(table)
                elif operation in ["getAll", "get"]:
                    reads.append(table)

        # HTTP Request to Supabase REST API
        if node.get("type") == "n8n-nodes-base.httpRequest":
            params = node.get("parameters", {})
            url = params.get("url", "")

            # Skip if url is not a string (can be dict in n8n expressions)
            if not isinstance(url, str):
                continue

            if "supabase" in url and "/rest/v1/" in url:
                # Extract table from URL
                match = re.search(r"/rest/v1/([a-zA-Z_]+)", url)
                if match:
                    table = match.group(1)
                    method = params.get("method", "GET")

                    if method in ["POST", "PATCH", "PUT", "DELETE"]:
                        writes.append(table)
                    else:
                        reads.append(table)

    return list(set(reads)), list(set(writes))


def extract_external_deps(nodes: list) -> list[str]:
    """Extract external service dependencies."""
    deps = []

    for node in nodes:
        node_type = node.get("type", "")
        params = node.get("parameters", {})

        # OpenAI
        if "openai" in node_type.lower() or "openAi" in node_type:
            deps.append("OpenAI")

        # Telegram
        if "telegram" in node_type.lower():
            deps.append("Telegram Bot API")

        # AssemblyAI
        if "assemblyai" in node_type.lower():
            deps.append("AssemblyAI")

        # HTTP to known services
        if node_type == "n8n-nodes-base.httpRequest":
            url = params.get("url", "")

            # Skip if url is not a string (can be dict in n8n expressions)
            if not isinstance(url, str):
                continue

            if "genomai.onrender.com" in url:
                if "/api/decision" in url:
                    deps.append("Decision Engine API")
                elif "/learning" in url:
                    deps.append("Learning Loop API")
            if "keitaro" in url.lower():
                deps.append("Keitaro API")
            if "drive.google" in url or "googleapis" in url:
                deps.append("Google Drive")

    return list(set(deps))


def extract_events_emitted(nodes: list) -> list[str]:
    """Extract event types emitted by workflow."""
    events = []

    for node in nodes:
        node_name = node.get("name", "").lower()
        params = node.get("parameters", {})

        # Look for "emit" in node name
        if "emit" in node_name:
            # Try to extract event type from node name
            # e.g., "Emit CreativeRegistered" -> "CreativeRegistered"
            match = re.search(r"emit\s+([a-zA-Z]+)", node.get("name", ""), re.IGNORECASE)
            if match:
                events.append(match.group(1))

        # Check for event_type in parameters
        if "event_type" in str(params):
            # Try to extract from JSON body or similar
            body = params.get("bodyParameters", params.get("jsonBody", ""))
            if isinstance(body, str):
                match = re.search(r'"event_type"\s*:\s*"([^"]+)"', body)
                if match:
                    events.append(match.group(1))

    return list(set(events))


def process_workflow(workflow: dict) -> dict:
    """Process a single workflow and extract dependencies."""
    nodes = workflow.get("nodes", [])

    # Determine trigger type
    trigger_types = {
        "n8n-nodes-base.webhook": "webhook",
        "n8n-nodes-base.scheduleTrigger": "schedule",
        "n8n-nodes-base.manualTrigger": "manual",
        "n8n-nodes-base.telegramTrigger": "telegram",
    }

    trigger = "unknown"
    for node in nodes:
        if node.get("type") in trigger_types:
            trigger = trigger_types[node["type"]]
            break

    reads, writes = extract_supabase_tables(nodes)
    calls = extract_webhook_calls(nodes)
    external = extract_external_deps(nodes)
    events = extract_events_emitted(nodes)

    return {
        "id": workflow.get("id", ""),
        "active": workflow.get("active", False),
        "trigger": trigger,
        "calls": calls,
        "writes": writes,
        "reads": reads,
        "events_emitted": events,
        "external_deps": external if external else [],
    }


def generate_mermaid_diagram(workflows: dict) -> str:
    """Generate Mermaid flowchart from workflow dependencies."""
    lines = [
        "flowchart TD",
        "",
        "    %% Auto-generated from n8n workflows",
        f"    %% Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
    ]

    # Group workflows by trigger type
    groups = {
        "telegram": [],
        "webhook": [],
        "schedule": [],
        "manual": [],
    }

    for name, info in workflows.items():
        trigger = info.get("trigger", "webhook")
        if trigger in groups:
            groups[trigger].append(name)

    # Add subgraphs
    if groups["telegram"]:
        lines.append("    subgraph Telegram[\"Telegram Entry Points\"]")
        for name in groups["telegram"]:
            short = name.replace("_", "")[:15]
            lines.append(f"        {short}[{name}]")
        lines.append("    end")
        lines.append("")

    if groups["schedule"]:
        lines.append("    subgraph Scheduled[\"Scheduled Jobs\"]")
        for name in groups["schedule"]:
            short = name.replace("_", "")[:15]
            lines.append(f"        {short}[{name}]")
        lines.append("    end")
        lines.append("")

    # Add connections
    lines.append("    %% Workflow calls")
    for name, info in workflows.items():
        source = name.replace("_", "")[:15]
        for target in info.get("calls", []):
            target_short = target.replace("_", "").replace("-", "")[:15]
            lines.append(f"    {source} --> {target_short}")

    return "\n".join(lines)


def sync_from_n8n(dry_run: bool = False, verbose: bool = False) -> bool:
    """Sync dependencies from n8n API."""
    print("=" * 60)
    print("GenomAI Dependency Sync")
    print("=" * 60)

    if not N8N_API_KEY:
        print("\n[SKIP] N8N_API_KEY not set - using existing manifest")
        print("Set N8N_API_KEY to enable auto-sync from n8n")
        return True

    print(f"\nAPI URL: {N8N_API_URL}")

    try:
        # Fetch all workflows
        print("\nFetching workflows from n8n...")
        response = api_request("workflows")
        workflows_list = response.get("data", [])
        print(f"Found {len(workflows_list)} workflows")

        # Process each workflow
        workflows = {}
        for wf in workflows_list:
            name = wf.get("name", "unknown").lower().replace(" ", "_").replace("-", "_")

            if verbose:
                print(f"\n  Processing: {name}")

            # Fetch full workflow details
            wf_detail = api_request(f"workflows/{wf['id']}")
            info = process_workflow(wf_detail)

            if verbose:
                print(f"    Trigger: {info['trigger']}")
                print(f"    Calls: {info['calls']}")
                print(f"    Writes: {info['writes']}")

            workflows[name] = info

        # Build manifest
        manifest = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "version": "1.0.0",
            "updated_at": datetime.now().strftime("%Y-%m-%d"),
            "description": "Auto-generated dependency manifest from n8n",
            "workflows": workflows,
        }

        # Generate Mermaid diagram
        mermaid = generate_mermaid_diagram(workflows)

        if dry_run:
            print("\n[DRY RUN] Would update:")
            print(f"  - {MANIFEST_PATH}")
            print(f"  - {GRAPH_PATH}")
            print("\nGenerated Mermaid:")
            print(mermaid[:500] + "...")
        else:
            # Write manifest
            with open(MANIFEST_PATH, "w") as f:
                json.dump(manifest, f, indent=2)
            print(f"\n[UPDATED] {MANIFEST_PATH}")

            # Update graph
            graph_content = f"""# Dependency Graph

Визуализация зависимостей между workflows, API и таблицами БД.

**Auto-generated from:** n8n API
**Last updated:** {datetime.now().strftime("%Y-%m-%d %H:%M")}

---

## Workflow Call Graph

```mermaid
{mermaid}
```

---

See `infrastructure/schemas/dependency_manifest.json` for full details.
"""
            with open(GRAPH_PATH, "w") as f:
                f.write(graph_content)
            print(f"[UPDATED] {GRAPH_PATH}")

        print("\n" + "=" * 60)
        print("SYNC COMPLETE")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n[ERROR] Sync failed: {e}")
        return False


def main():
    dry_run = "--dry-run" in sys.argv
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    success = sync_from_n8n(dry_run=dry_run, verbose=verbose)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

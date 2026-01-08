# n8n Workflows Archive

**Status:** DEPRECATED
**Migration:** n8n → Temporal (Issue #241)
**Archive Date:** 2026-01-08

## Overview

This directory contains archived n8n workflow JSON exports.
All workflows have been migrated to Temporal.

## Archived Workflows

### Legacy Workflows (Inactive)

| n8n ID | Name | Status |
|--------|------|--------|
| `4fRlGSpAV2o9NUCo` | Performance Metrics Collector | Replaced by Keitaro Poller |
| `8k0zMto3UjiEYyxi` | Backfill Cost for Historical Queue | Manual utility |
| `A8gKvO5810L1lusZ` | Buyer Historical URL Handler | Replaced by v2 |
| `O8SPLlixny3MHvxO` | Telegram Creative Ingestion | Legacy |
| `RLO7XEoDV3lj74cl` | Historical Import Batch Loader | Manual utility |
| `zMHVFT2rM7PpTiJj` | Outcome Ingestion Keitaro | Legacy, replaced |

### Deleted Workflows

| n8n ID | Name | Reason |
|--------|------|--------|
| `ClXUPP2IvWRgu99y` | keep_alive_decision_engine | Not needed with Temporal |

## Migration Map

See [docs/TEMPORAL_WORKFLOWS.md](../../docs/TEMPORAL_WORKFLOWS.md) for complete migration mapping.

## Restoration

**DO NOT** restore these workflows. Use Temporal workflows instead.

If you need to reference old workflow logic:
1. Check JSON files in this directory
2. Compare with Temporal workflow implementation in `decision-engine-service/temporal/`

## n8n Account

The n8n Cloud account should be kept for 30 days after full migration as rollback safety.
After 30 days, account can be cancelled.

**n8n Cloud URL:** https://kazamaqwe.app.n8n.cloud

# AI Data Training Pipeline — M1: Ingestion

Bash script that ingests raw multi-format files, routes them by type,
deduplicates via SHA-256 checksum, logs to a persistent master log.

## Stack
Bash, sha256sum, awk

## Bugs found and fixed during build (not copy-pasted)
1. Missing `$` on `RAW_DIR` reference — loop iterated over literal
   string instead of expanding variable, script exited silently
   with no error (caught via `bash -x`).
2. Log file re-created per run with timestamp — dedup check searched
   an empty file every time, duplicates were never caught. Fixed by
   splitting into a fixed MASTER_LOG (persistent) + per-run LOG_FILE
   (audit trail).
3. Missing `$` on `STRUCT_DIR` inside `dest_dir` — `set -u` didn't
   catch it because it wasn't a variable reference, just a typo string.

## Sample run
```
Mon Jul 20 11:48:06 AM PKT 2026: INGESTED data1.json -> structured/json | sha256=987e04d5...
Mon Jul 20 11:51:10 AM PKT 2026: DUPLICATE skipped -> data1.json (987e04d5...)
```

## Next
M2 — cleaning, labeling, HITL gate for ambiguous/sensitive rows, PII scrub.

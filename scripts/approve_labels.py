#!/usr/bin/env python3
import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path.home() / "ai-data-training"
QUEUE_FILE = BASE / "cleaned" / "review_queue.jsonl"
LABELED_FILE = BASE / "cleaned" / "labeled.jsonl"
DISCARD_LOG = BASE / "logs" / "discarded.log"

VALID_LABELS = {"failure", "success", "skip"}


def main():
    if not QUEUE_FILE.exists():
        print("No review queue found. Run clean_label.py first.")
        return

    with open(QUEUE_FILE) as f:
        rows = [json.loads(line) for line in f if line.strip()]

    if not rows:
        print("Review queue is empty. Nothing to approve.")
        return

    remaining, approved, discard_log_lines = [], [], []

    for i, row in enumerate(rows):
        print(f"\n[{i+1}/{len(rows)}] source: {row['source']}")
        print(f"text: {row['text']}")
        choice = input("Label (failure / success / skip / stop): ").strip().lower()

        if choice == "stop":
            remaining.extend(rows[i:])
            break
        if choice not in VALID_LABELS:
            print("Invalid input, keeping in queue.")
            remaining.append(row)
            continue
        if choice == "skip":
            discard_log_lines.append(
                f"{datetime.now(timezone.utc).isoformat()} | {row['source']} | {row.get('raw_hash','')} | skipped by human | text=\"{row['text']}\""
            )
            continue
        row["label"] = choice
        row["labeled_by"] = "human"
        approved.append(row)

    if approved:
        with open(LABELED_FILE, "a") as f:
            for r in approved:
                f.write(json.dumps(r) + "\n")

    with open(QUEUE_FILE, "w") as f:
        for r in remaining:
            f.write(json.dumps(r) + "\n")

    if discard_log_lines:
        with open(DISCARD_LOG, "a") as f:
            for line in discard_log_lines:
                f.write(line + "\n")

    print(f"\nApproved and moved to labeled.jsonl: {len(approved)}")
    print(f"Still in review queue: {len(remaining)}")
    print(f"Skipped (logged to discarded.log): {len(discard_log_lines)}")


if __name__ == "__main__":
    main()

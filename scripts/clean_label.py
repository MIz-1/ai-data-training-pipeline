#!/usr/bin/env python3
import json
import re
import csv
import hashlib
from pathlib import Path
from datetime import datetime, timezone

BASE = Path.home() / "ai-data-training"
STRUCT_DIR = BASE / "structured"
CLEANED_DIR = BASE / "cleaned"
LOG_FILE = BASE / "logs" / "pii_scrub.log"
CHANGE_LOG = BASE / "logs" / "content_changed.log"
DISCARD_LOG = BASE / "logs" / "discarded.log"
LABELED_FILE = CLEANED_DIR / "labeled.jsonl"
QUEUE_FILE = CLEANED_DIR / "review_queue.jsonl"

CLEANED_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b")
CARD_RE = re.compile(r"\bcard ending \d{4}\b", re.IGNORECASE)

FAIL_WORDS = {"error", "fail", "failed", "crash", "crashed", "fatal", "timeout"}
SUCCESS_WORDS = {"success", "ok", "completed successfully", "shipped", "no issues", "working fine"}


def raw_hash(text):
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def scrub_pii(text, source_id, log_lines):
    def _redact(pattern, label, s):
        def repl(m):
            h = hashlib.sha256(m.group(0).encode()).hexdigest()[:10]
            log_lines.append(f"{datetime.now(timezone.utc).isoformat()} | {source_id} | {label} | hash={h}")
            return f"[{label}_REDACTED]"
        return pattern.sub(repl, s)
    text = _redact(EMAIL_RE, "EMAIL", text)
    text = _redact(PHONE_RE, "PHONE", text)
    text = _redact(CARD_RE, "CARD", text)
    return text


def rule_label(text):
    lower = text.lower()
    has_fail = any(w in lower for w in FAIL_WORDS)
    has_success = any(w in lower for w in SUCCESS_WORDS)
    if has_fail and not has_success:
        return "failure"
    if has_success and not has_fail:
        return "success"
    return "ambiguous"


def load_records():
    for jf in sorted((STRUCT_DIR / "json").glob("*.json")):
        with open(jf) as f:
            for i, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    yield f"{jf.name}:{i}", obj.get("text", "")
                except json.JSONDecodeError:
                    yield f"{jf.name}:{i}", line

    for cf in sorted((STRUCT_DIR / "csv").glob("*.csv")):
        with open(cf) as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                yield f"{cf.name}:{i}", row.get("text", "")

    for lf in sorted((STRUCT_DIR / "log").glob("*.log")):
        with open(lf) as f:
            for i, line in enumerate(f):
                line = line.strip()
                if line:
                    yield f"{lf.name}:{i}", line


def load_existing(path):
    result = {}
    if path.exists():
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                result[rec["source"]] = rec
    return result


def load_discarded():
    result = {}
    if DISCARD_LOG.exists():
        with open(DISCARD_LOG) as f:
            for line in f:
                parts = line.strip().split(" | ")
                if len(parts) >= 4 and parts[3] == "skipped by human":
                    result[parts[1]] = parts[2]
    return result


def main():
    log_lines = []
    change_log_lines = []

    existing_labeled = load_existing(LABELED_FILE)
    existing_queue = load_existing(QUEUE_FILE)
    discarded = load_discarded()
    known = {**existing_queue, **existing_labeled}

    final_labeled = dict(existing_labeled)
    final_queue = dict(existing_queue)

    new_count, unchanged_count, changed_count = 0, 0, 0

    for source_id, text in load_records():
        if not text:
            continue
        h = raw_hash(text)

        if source_id in discarded and discarded[source_id] == h:
            unchanged_count += 1
            continue

        if source_id in known and known[source_id].get("raw_hash") == h:
            unchanged_count += 1
            continue

        if source_id in known:
            changed_count += 1
            change_log_lines.append(
                f"{datetime.now(timezone.utc).isoformat()} | {source_id} | content changed, reprocessed"
            )
            final_labeled.pop(source_id, None)
            final_queue.pop(source_id, None)
        else:
            new_count += 1

        clean_text = scrub_pii(text, source_id, log_lines)
        label = rule_label(clean_text)
        record = {"source": source_id, "text": clean_text, "label": label, "raw_hash": h}

        if label == "ambiguous":
            final_queue[source_id] = record
        else:
            final_labeled[source_id] = record

    with open(LABELED_FILE, "w") as f:
        for rec in final_labeled.values():
            f.write(json.dumps(rec) + "\n")

    with open(QUEUE_FILE, "w") as f:
        for rec in final_queue.values():
            f.write(json.dumps(rec) + "\n")

    if log_lines:
        with open(LOG_FILE, "a") as f:
            for line in log_lines:
                f.write(line + "\n")

    if change_log_lines:
        with open(CHANGE_LOG, "a") as f:
            for line in change_log_lines:
                f.write(line + "\n")

    print(f"New rows processed: {new_count}")
    print(f"Unchanged, preserved as-is: {unchanged_count}")
    print(f"Changed since last run, reprocessed: {changed_count}")
    print(f"Total labeled: {len(final_labeled)} | Total in review queue: {len(final_queue)}")


if __name__ == "__main__":
    main()

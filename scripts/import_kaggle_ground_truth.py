import csv
import json
import sys
sys.path.insert(0, "scripts")
from clean_label import scrub_pii, raw_hash, LABELED_FILE, QUEUE_FILE

INPUT = "raw_data/customer_support_tickets.csv"

def purge_old_kaggle_entries(path):
    if not path.exists():
        return []
    kept = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if not rec["source"].startswith("kaggle_support_tickets.csv:"):
                kept.append(rec)
    return kept

def main():
    kept_labeled = purge_old_kaggle_entries(LABELED_FILE)
    kept_queue = purge_old_kaggle_entries(QUEUE_FILE)

    new_records = []
    log_lines = []
    skipped_no_rating = 0

    with open(INPUT, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            status = row.get("Ticket Status", "")
            rating = row.get("Customer Satisfaction Rating", "")
            if status != "Closed" or not rating:
                skipped_no_rating += 1
                continue

            source_id = f"kaggle_ground_truth:{i}"
            email = row.get("Customer Email", "")
            desc = row.get("Ticket Description", "")
            text = f"Customer email: {email}. Issue: {desc}"

            h = raw_hash(text)
            clean_text = scrub_pii(text, source_id, log_lines)
            label = "success" if float(rating) >= 3 else "failure"

            new_records.append({
                "source": source_id,
                "text": clean_text,
                "label": label,
                "raw_hash": h,
                "labeled_by": "kaggle_rating"
            })

    all_labeled = kept_labeled + new_records

    with open(LABELED_FILE, "w") as f:
        for rec in all_labeled:
            f.write(json.dumps(rec) + "\n")

    with open(QUEUE_FILE, "w") as f:
        for rec in kept_queue:
            f.write(json.dumps(rec) + "\n")

    print(f"Imported {len(new_records)} ground-truth rows.")
    print(f"Skipped (no rating / not closed): {skipped_no_rating}")
    print(f"Purged old rule-based kaggle entries from labeled + queue.")
    print(f"Final labeled.jsonl total: {len(all_labeled)}")
    print(f"Final review_queue.jsonl total: {len(kept_queue)}")

if __name__ == "__main__":
    main()

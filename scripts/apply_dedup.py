import json

LABELED_FILE = "cleaned/labeled.jsonl"
CLUSTERS_FILE = "near_dupe_clusters.json"

def main():
    with open(CLUSTERS_FILE) as f:
        clusters = json.load(f)

    to_remove = set()
    for cluster in clusters:
        # keep first, drop rest
        for rid in cluster[1:]:
            to_remove.add(rid)

    rows = []
    with open(LABELED_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))

    before = len(rows)
    kept = [r for r in rows if r["source"] not in to_remove]
    after = len(kept)

    with open(LABELED_FILE, "w") as f:
        for r in kept:
            f.write(json.dumps(r) + "\n")

    print(f"Rows before: {before}")
    print(f"Rows removed (near-dupes): {before - after}")
    print(f"Rows after: {after}")

if __name__ == "__main__":
    main()

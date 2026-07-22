import json
from datasketch import MinHash, MinHashLSH

INPUT_FILE = "cleaned/labeled.jsonl"
TEXT_KEY = "text"
ID_KEY = "source"
THRESHOLD = 0.75
NUM_PERM = 128
NGRAM_SIZE = 3

def load_rows(path):
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows

def shingles(text, n=NGRAM_SIZE):
    words = text.split()
    if len(words) < n:
        return [" ".join(words)] if words else [""]
    return [" ".join(words[i:i+n]) for i in range(len(words) - n + 1)]

def build_minhash(text):
    m = MinHash(num_perm=NUM_PERM)
    for sh in shingles(text):
        m.update(sh.encode("utf8"))
    return m

def main():
    rows = load_rows(INPUT_FILE)
    print(f"Loaded {len(rows)} rows.")

    lsh = MinHashLSH(threshold=THRESHOLD, num_perm=NUM_PERM)
    minhashes = {}

    for row in rows:
        rid = row[ID_KEY]
        text = row.get(TEXT_KEY, "") or ""
        m = build_minhash(text)
        minhashes[rid] = m
        lsh.insert(rid, m)

    seen = set()
    clusters = []

    for row in rows:
        rid = row[ID_KEY]
        if rid in seen:
            continue
        matches = [m for m in lsh.query(minhashes[rid]) if m != rid]
        if matches:
            cluster = [rid] + matches
            clusters.append(cluster)
            seen.update(cluster)

    print(f"Found {len(clusters)} near-duplicate clusters covering {sum(len(c) for c in clusters)} rows.")

    with open("near_dupe_clusters.json", "w") as f:
        json.dump(clusters, f, indent=2)

    print("Written to near_dupe_clusters.json")

if __name__ == "__main__":
    main()

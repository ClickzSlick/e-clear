import json
from pathlib import Path

DATA_DIR   = Path("data")
DEPLOY_DIR = Path("data/dataset")
DEPLOY_DIR.mkdir(parents=True, exist_ok=True)

# ── Step 1: Load reviews (cap at 50k) and track active users/businesses ────────
print("Processing reviews...")
reviews = []
with open(DATA_DIR / "yelp_academic_dataset_review.json", encoding="utf-8", errors="replace") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
            if r.get("text", "").strip():
                reviews.append(r)
        except:
            continue
        if len(reviews) >= 50_000:
            break

active_user_ids     = set(r["user_id"]     for r in reviews)
active_business_ids = set(r["business_id"] for r in reviews)

print(f"Kept {len(reviews)} reviews")
print(f"Active users: {len(active_user_ids)}")
print(f"Active businesses: {len(active_business_ids)}")

# ── Step 2: Save filtered reviews ─────────────────────────────────────────────
out_reviews = DEPLOY_DIR / "yelp_academic_dataset_review.json"
with open(out_reviews, "w", encoding="utf-8") as f:
    for r in reviews:
        f.write(json.dumps(r) + "\n")
print(f"Saved reviews → {out_reviews} ({out_reviews.stat().st_size / 1e6:.1f}MB)")

# ── Step 3: Filter businesses to only active ones ──────────────────────────────
print("Filtering businesses...")
businesses = []
with open(DATA_DIR / "yelp_academic_dataset_business.json", encoding="utf-8", errors="replace") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            b = json.loads(line)
            if b["business_id"] in active_business_ids:
                businesses.append(b)
        except:
            continue

out_biz = DEPLOY_DIR / "yelp_academic_dataset_business.json"
with open(out_biz, "w", encoding="utf-8") as f:
    for b in businesses:
        f.write(json.dumps(b) + "\n")
print(f"Saved businesses → {out_biz} ({out_biz.stat().st_size / 1e6:.1f}MB)")
print(f"Businesses kept: {len(businesses)}")

# ── Step 4: Filter users to only active ones ───────────────────────────────────
print("Filtering users...")
users = []
with open(DATA_DIR / "yelp_academic_dataset_user.json", encoding="utf-8", errors="replace") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            u = json.loads(line)
            if u["user_id"] in active_user_ids:
                users.append(u)
        except:
            continue

out_users = DEPLOY_DIR / "yelp_academic_dataset_user.json"
with open(out_users, "w", encoding="utf-8") as f:
    for u in users:
        f.write(json.dumps(u) + "\n")
print(f"Saved users → {out_users} ({out_users.stat().st_size / 1e6:.1f}MB)")
print(f"Users kept: {len(users)}")

# ── Step 5: Copy the CSV files across too ─────────────────────────────────────
import shutil

csv_files = [
    "books.csv",
    "nigeria_food_jumia.csv",
    "Nigerian_Foods.csv",
]

print("Copying CSV files...")
for fname in csv_files:
    src = DATA_DIR / fname
    dst = DEPLOY_DIR / fname
    if src.exists():
        shutil.copy2(src, dst)
        print(f"Copied → {dst} ({dst.stat().st_size / 1e6:.2f}MB)")
    else:
        print(f"Skipped {fname} — not found in data/")

# ── Step 6: Summary ────────────────────────────────────────────────────────────
print("\n── Summary ───────────────────────────────────────────")
total = 0
for f in sorted(DEPLOY_DIR.iterdir()):
    size = f.stat().st_size / 1e6
    total += size
    print(f"  {f.name:<50} {size:.1f}MB")
print(f"\n  Total: {total:.1f}MB")
print(f"\nOriginal files in data/ are untouched.")
print(f"Deploy-ready files are in data/dataset/")
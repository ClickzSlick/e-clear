# import json
# from pathlib import Path


# # This is our internal standard schema.
# # Every dataset gets converted to this. Core logic never sees raw files.

# def normalize_yelp(data_dir: str) -> dict:
#     """
#     Loads Yelp JSON files and returns normalized lookup structures.
#     Returns: businesses dict, users dict, reviews list
#     """
#     data_path = Path(data_dir)

#     print("Loading businesses...")
#     businesses = {}
#     with open(data_path / "yelp_academic_dataset_business.json", "r", encoding="utf-8") as f:
#         for line in f:
#             b = json.loads(line)
#             businesses[b["business_id"]] = {
#                 "item_id": b["business_id"],
#                 "item_name": b.get("name", ""),
#                 "item_category": b.get("categories", ""),
#                 "city": b.get("city", ""),
#                 "state": b.get("state", ""),
#             }

#     print(f"Loaded {len(businesses)} businesses")

#     print("Loading users...")
#     users = {}
#     with open(data_path / "yelp_academic_dataset_user.json", "r", encoding="utf-8") as f:
#         for line in f:
#             line = line.strip()
#             if not line:
#                 continue
#             try:
#                 u = json.loads(line)
#                 users[u["user_id"]] = {
#                     "user_id": u["user_id"],
#                     "name": u.get("name", ""),
#                     "review_count": u.get("review_count", 0),
#                     "yelping_since": u.get("yelping_since", ""),
#                 }
#             except json.JSONDecodeError:
#                 continue  # skip malformed lines silently

#     print(f"Loaded {len(users)} users")

#     print("Loading reviews (capped at 200k)...")
#     reviews = []
#     errors_skipped = 0
#     with open(data_path / "yelp_academic_dataset_review.json", "r", encoding="utf-8", errors="replace") as f:
#         for line in f:
#             line = line.strip()
#             if not line:
#                 continue
#             try:
#                 r = json.loads(line)
#                 text = r.get("text", "").strip()
#                 if not text:
#                     continue
#                 reviews.append({
#                     "user_id": r["user_id"],
#                     "item_id": r["business_id"],
#                     "rating": r["stars"],
#                     "review_text": text,
#                     "date": r["date"],
#                 })
#             except Exception:
#                 errors_skipped += 1
#                 continue

#             if len(reviews) >= 200_000:
#                 break

#     print(f"Loaded {len(reviews)} reviews (skipped {errors_skipped} malformed lines)")
#     return businesses, users, reviews


# def get_user_history(user_id: str, reviews: list, businesses: dict, limit: int = 20) -> list:
#     """
#     Given a user_id, return their review history in standard format.
#     This is the core input to persona building.
#     """
#     history = []
#     for r in reviews:
#         if r["user_id"] == user_id:
#             business = businesses.get(r["item_id"], {})
#             history.append({
#                 "user_id": user_id,
#                 "item_id": r["item_id"],
#                 "item_name": business.get("item_name", "Unknown"),
#                 "item_category": business.get("item_category", ""),
#                 "rating": r["rating"],
#                 "review_text": r["review_text"],
#                 "date": r["date"],
#             })
#         if len(history) >= limit:
#             break

#     return sorted(history, key=lambda x: x["date"], reverse=True)

import json
import csv
import hashlib
from pathlib import Path


# ── Internal Standard Schema ───────────────────────────────────────────────────
# Every dataset gets normalized to this. Core logic never sees raw files.
# Reviews:   { user_id, item_id, rating, review_text, date }
# Businesses: { item_id, item_name, item_category, city, state }


# ── Yelp ───────────────────────────────────────────────────────────────────────

def normalize_yelp(data_dir: str) -> tuple:
    """
    Loads Yelp JSON files and returns normalized lookup structures.
    Returns: businesses dict, users dict, reviews list
    """
    data_path = Path(data_dir)

    print("Loading businesses...")
    businesses = {}
    with open(data_path / "yelp_academic_dataset_business.json", "r", encoding="utf-8") as f:
        for line in f:
            b = json.loads(line)
            businesses[b["business_id"]] = {
                "item_id": b["business_id"],
                "item_name": b.get("name", ""),
                "item_category": b.get("categories", "") or "",
                "city": b.get("city", ""),
                "state": b.get("state", ""),
                "source": "yelp",
            }
    print(f"Loaded {len(businesses)} businesses")

    print("Loading users...")
    users = {}
    with open(data_path / "yelp_academic_dataset_user.json", "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                u = json.loads(line)
                users[u["user_id"]] = {
                    "user_id": u["user_id"],
                    "name": u.get("name", ""),
                    "review_count": u.get("review_count", 0),
                    "yelping_since": u.get("yelping_since", ""),
                }
            except json.JSONDecodeError:
                continue

    print(f"Loaded {len(users)} users")

    print("Loading reviews (capped at 200k)...")
    reviews = []
    errors_skipped = 0
    with open(data_path / "yelp_academic_dataset_review.json", "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
                text = r.get("text", "").strip()
                if not text:
                    continue
                reviews.append({
                    "user_id": r["user_id"],
                    "item_id": r["business_id"],
                    "rating": r["stars"],
                    "review_text": text,
                    "date": r["date"],
                    "source": "yelp",
                })
            except Exception:
                errors_skipped += 1
                continue
            if len(reviews) >= 200_000:
                break

    print(f"Loaded {len(reviews)} reviews (skipped {errors_skipped} malformed lines)")
    return businesses, users, reviews


# ── Goodreads Books (books.csv) ────────────────────────────────────────────────

def normalize_books(data_dir: str) -> dict:
    """
    Loads books.csv (Goodreads catalog) as an item pool for cross-domain
    recommendations. No per-user reviews — aggregate ratings only.

    Columns: bookID, title, authors, average_rating, isbn, isbn13,
             language_code, num_pages, ratings_count, text_reviews_count,
             publication_date, publisher
    """
    data_path = Path(data_dir)
    filepath = data_path / "books.csv"

    if not filepath.exists():
        print("Warning: books.csv not found, skipping.")
        return {}

    books = {}
    errors = 0

    print("Loading books catalog...")
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                book_id = f"book_{row['bookID'].strip()}"
                # Only include English books with meaningful review counts
                if row.get("language_code", "").strip() not in ("eng", "en-US", "en-GB", ""):
                    continue
                ratings_count = int(row.get("ratings_count", "0").strip() or 0)
                if ratings_count < 100:
                    continue

                books[book_id] = {
                    "item_id": book_id,
                    "item_name": row["title"].strip(),
                    "item_category": f"Books, {_infer_book_genre(row['title'])}",
                    "authors": row.get("authors", "").strip(),
                    "avg_rating": float(row.get("average_rating", "0").strip() or 0),
                    "ratings_count": ratings_count,
                    "num_pages": row.get("  num_pages", row.get("num_pages", "0")).strip(),
                    "publisher": row.get("publisher", "").strip(),
                    "city": "",
                    "state": "",
                    "source": "goodreads",
                }
            except Exception:
                errors += 1
                continue

    print(f"Loaded {len(books)} books (skipped {errors} rows)")
    return books


def _infer_book_genre(title: str) -> str:
    """
    Simple keyword-based genre inference from title.
    Helps the cross-domain recommender filter by sub-genre.
    """
    title_lower = title.lower()
    if any(w in title_lower for w in ["harry potter", "fantasy", "dragon", "magic", "wizard"]):
        return "Fantasy"
    if any(w in title_lower for w in ["murder", "detective", "crime", "thriller", "mystery"]):
        return "Thriller"
    if any(w in title_lower for w in ["love", "romance", "heart", "kiss"]):
        return "Romance"
    if any(w in title_lower for w in ["history", "war", "empire", "revolution"]):
        return "History"
    if any(w in title_lower for w in ["science", "physics", "biology", "cosmos", "brain"]):
        return "Science"
    if any(w in title_lower for w in ["business", "money", "leadership", "startup", "habits"]):
        return "Business"
    if any(w in title_lower for w in ["cook", "recipe", "food", "eat"]):
        return "Cooking"
    return "General"


# ── Jumia Nigeria Food Products (nigeria_food_jumia.csv) ──────────────────────

def normalize_jumia(data_dir: str) -> dict:
    """
    Loads nigeria_food_jumia.csv as a Nigerian food item pool.
    Useful for cross-domain recommendations in the Nigerian food context.

    Columns: Name, Current Price ₦, Old Price ₦, % discount,
             Rating, Review Count, Shipped?, Official Store?
    """
    data_path = Path(data_dir)
    filepath = data_path / "nigeria_food_jumia.csv"

    if not filepath.exists():
        print("Warning: nigeria_food_jumia.csv not found, skipping.")
        return {}

    items = {}
    errors = 0

    print("Loading Jumia Nigeria food products...")
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                name = row.get("Name", "").strip()
                if not name:
                    continue

                # Parse rating — some rows have "n/a"
                raw_rating = row.get("Rating", "").strip()
                avg_rating = float(raw_rating) if raw_rating not in ("n/a", "", "N/A") else None

                # Skip items with no rating and no reviews
                review_count = int(row.get("Review Count", "0").strip() or 0)
                if avg_rating is None and review_count == 0:
                    continue

                # Generate a stable item_id from the name
                item_id = f"jumia_{hashlib.md5(name.encode()).hexdigest()[:10]}"

                # Parse price
                raw_price = row.get("Current Price ₦", "").strip().replace(",", "")
                try:
                    price = float(raw_price)
                    price_context = f"₦{raw_price}"
                except Exception:
                    price_context = "Price unavailable"

                # Discount context
                discount = row.get("% discount", "0%").strip()
                official = row.get("Official Store?", "no").strip().lower() == "yes"

                items[item_id] = {
                    "item_id": item_id,
                    "item_name": name,
                    "item_category": "Nigerian Food, Food Products, Groceries",
                    "avg_rating": avg_rating or 3.5,
                    "review_count": review_count,
                    "price": price_context,
                    "discount": discount,
                    "official_store": official,
                    "city": "Nigeria",
                    "state": "",
                    "source": "jumia",
                }
            except Exception:
                errors += 1
                continue

    print(f"Loaded {len(items)} Jumia food products (skipped {errors} rows)")
    return items


# ── Nigerian Foods Knowledge Base (Nigerian_Foods.csv) ────────────────────────

def normalize_nigerian_foods(data_dir: str) -> dict:
    """
    Loads Nigerian_Foods.csv as a cultural food knowledge base.
    Enriches the item pool with traditional Nigerian food metadata —
    region, spice level, health classification, price range.

    Columns: Food_Name, Main_Ingredients, Description, Food_Health,
             Food_Class, Region, Spice_Level, Price_Range
    """
    data_path = Path(data_dir)
    filepath = data_path / "Nigerian_Foods.csv"

    if not filepath.exists():
        print("Warning: Nigerian_Foods.csv not found, skipping.")
        return {}

    foods = {}
    errors = 0

    print("Loading Nigerian foods knowledge base...")
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                name = row.get("Food_Name", "").strip()
                if not name:
                    continue

                item_id = f"ngfood_{hashlib.md5(name.encode()).hexdigest()[:10]}"

                region = row.get("Region", "").strip()
                spice = row.get("Spice_Level", "").strip()
                food_class = row.get("Food_Class", "").strip()
                price_range = row.get("Price_Range", "").strip()
                health = row.get("Food_Health", "").strip()
                description = row.get("Description", "").strip()
                ingredients = row.get("Main_Ingredients", "").strip()

                # Build a rich category string for filtering
                category_parts = ["Nigerian Food", "Traditional Nigerian"]
                if food_class:
                    category_parts.append(food_class)
                if region:
                    category_parts.append(f"{region} Cuisine")

                # Build a human-readable description for the LLM to reason about
                item_description = (
                    f"{description} "
                    f"Ingredients: {ingredients}. "
                    f"Spice level: {spice}. "
                    f"Health: {health}. "
                    f"Price range: {price_range}."
                ).strip()

                foods[item_id] = {
                    "item_id": item_id,
                    "item_name": name,
                    "item_category": ", ".join(category_parts),
                    "item_description": item_description,
                    "region": region,
                    "spice_level": spice,
                    "price_range": price_range,
                    "food_class": food_class,
                    "health": health,
                    "city": region,
                    "state": "Nigeria",
                    "avg_rating": 4.0,  # no ratings in dataset, use neutral default
                    "source": "nigerian_foods",
                }
            except Exception:
                errors += 1
                continue

    print(f"Loaded {len(foods)} Nigerian foods (skipped {errors} rows)")
    return foods


# ── Combined Loader ────────────────────────────────────────────────────────────

def load_all_businesses(data_dir: str, yelp_businesses: dict) -> dict:
    """
    Merges Yelp businesses with all supplementary item pools.
    Call this after normalize_yelp to get the full combined item catalog.
    """
    all_businesses = dict(yelp_businesses)

    books = normalize_books(data_dir)
    all_businesses.update(books)

    jumia = normalize_jumia(data_dir)
    all_businesses.update(jumia)

    ng_foods = normalize_nigerian_foods(data_dir)
    all_businesses.update(ng_foods)

    print(f"Total combined item pool: {len(all_businesses)} items")
    return all_businesses


# ── User History ───────────────────────────────────────────────────────────────

def get_user_history(user_id: str, reviews: list, businesses: dict, limit: int = 20) -> list:
    """
    Given a user_id, return their review history in standard format.
    This is the core input to persona building.
    """
    history = []
    for r in reviews:
        if r["user_id"] == user_id:
            business = businesses.get(r["item_id"], {})
            history.append({
                "user_id": user_id,
                "item_id": r["item_id"],
                "item_name": business.get("item_name", "Unknown"),
                "item_category": business.get("item_category", "") or "",
                "rating": r["rating"],
                "review_text": r["review_text"],
                "date": r["date"],
                "source": r.get("source", "yelp"),
            })
        if len(history) >= limit:
            break

    return sorted(history, key=lambda x: x["date"], reverse=True)
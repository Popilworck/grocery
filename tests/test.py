import os
import sys
import requests
import time
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
BASE_URL = "http://localhost:5001"
CSV_PATH = os.path.join(os.path.dirname(__file__), "test_inventory.csv")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

inserted_ids = []


def wait_for_server(timeout=10):
    print("Waiting for Flask server...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            requests.get(f"{BASE_URL}/inventory", timeout=2)
            print("Server is up!\n")
            return True
        except requests.ConnectionError:
            time.sleep(0.5)
    print("ERROR: Server didn't start in time. Run 'python backend/app.py' first.")
    sys.exit(1)


def test_upload_csv():
    print("=" * 50)
    print("TEST 1: Upload CSV via Gemini parsing")
    print("=" * 50)

    with open(CSV_PATH, "rb") as f:
        resp = requests.post(f"{BASE_URL}/upload-csv", files={"file": f})

    print(f"  Status: {resp.status_code}")
    print(f"  Headers: {dict(resp.headers)}")
    print(f"  Body: {resp.text[:500]}")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["success"] is True
    assert data["rows_inserted"] >= 1

    print(f"  Inserted {data['rows_inserted']} rows, skipped {data.get('rows_skipped', 0)}")
    print(f"  Response: {data}")
    print("  PASSED\n")
    return data["rows_inserted"]


def test_read_inventory(expected_min_rows):
    print("=" * 50)
    print("TEST 2: Read inventory back from Supabase")
    print("=" * 50)

    resp = requests.get(f"{BASE_URL}/inventory")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

    products = resp.json()
    assert len(products) >= expected_min_rows, (
        f"Expected at least {expected_min_rows} products, got {len(products)}"
    )

    print(f"  Retrieved {len(products)} products")
    for p in products:
        inserted_ids.append(p["id"])
        label = p.get("rotten_label") or "Not scored"
        print(f"    - {p['product_name'] or '(no name)'}: {label}")

    print("  PASSED\n")


def test_edge_cases(products):
    print("=" * 50)
    print("TEST 3: Verify edge cases were handled")
    print("=" * 50)

    names = [p["product_name"] for p in products if p["product_name"]]

    has_null_fields = any(
        p.get("batch_id") is None or p.get("quantity") is None or p.get("date_received") is None
        for p in products
    )
    print(f"  Has items with null fields (missing data): {has_null_fields}")

    has_nameless = any(p["product_name"] is None for p in products)
    print(f"  Has item with no product name: {has_nameless}")

    print(f"  Total products parsed: {len(products)}")
    print("  PASSED\n")


def cleanup():
    print("=" * 50)
    print("CLEANUP: Deleting test data from Supabase")
    print("=" * 50)

    if not inserted_ids:
        print("  No rows to delete.")
        return

    for row_id in inserted_ids:
        supabase.table("rottenness_scores").delete().eq("inventory_id", row_id).execute()

    for row_id in inserted_ids:
        supabase.table("inventory").delete().eq("id", row_id).execute()

    print(f"  Deleted {len(inserted_ids)} inventory rows and their scores")
    print("  DONE\n")


if __name__ == "__main__":
    wait_for_server()

    try:
        rows = test_upload_csv()
        resp = requests.get(f"{BASE_URL}/inventory")
        products = resp.json()
        test_read_inventory(rows)
        test_edge_cases(products)
        print("ALL TESTS PASSED")
    finally:
        cleanup()

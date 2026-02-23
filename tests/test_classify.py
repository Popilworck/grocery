"""
End-to-end test for the /classify endpoint.
Uses a sample fruit image to verify the full ML pipeline:
  image upload → classification → Supabase score write → cleanup
"""

import os
import sys
import requests
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
BASE_URL = "http://localhost:5001"

IMAGE_PATH = os.path.join(os.path.dirname(__file__), "..", "ml", "sample_images", "orange.png")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

test_inventory_id = None


def wait_for_server(timeout=10):
    print("Waiting for Flask server...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            requests.get(f"{BASE_URL}/inventory", timeout=2)
            print("Server is up!\n")
            return
        except requests.ConnectionError:
            time.sleep(0.5)
    print("ERROR: Server not running. Start it with: python backend/app.py")
    sys.exit(1)


def setup_test_inventory():
    """Insert a temporary inventory row so we can attach a score to it."""
    global test_inventory_id
    result = supabase.table("inventory").insert({
        "product_name": "Test Orange",
        "category": "Fruit",
        "quantity": 10,
        "unit": "lbs",
    }).execute()
    test_inventory_id = result.data[0]["id"]
    print(f"  Created test inventory row (id={test_inventory_id})\n")


def test_classify_basic():
    print("=" * 55)
    print("TEST 1: Classify image (no inventory link)")
    print("=" * 55)

    with open(IMAGE_PATH, "rb") as f:
        resp = requests.post(f"{BASE_URL}/classify", files={"file": f})

    print(f"  Status:     {resp.status_code}")
    data = resp.json()
    print(f"  Prediction: {data.get('prediction')}")
    print(f"  Confidence: {data.get('confidence')}%")
    print(f"  Rot score:  {data.get('rot_score')}")
    print(f"  Status:     {data.get('status')}")
    print(f"  Method:     {data.get('method')}")

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    assert data["prediction"] in ("fresh", "stale", "rotten"), f"Unexpected prediction: {data['prediction']}"
    assert 0 <= data["confidence"] <= 100
    assert 0.0 <= data["rot_score"] <= 1.0
    assert data["status"] in ("good", "warning", "bad")
    print("  PASSED\n")


def test_classify_with_score():
    print("=" * 55)
    print("TEST 2: Classify + write score to Supabase")
    print("=" * 55)

    with open(IMAGE_PATH, "rb") as f:
        resp = requests.post(
            f"{BASE_URL}/classify",
            files={"file": f},
            data={"inventory_id": str(test_inventory_id)},
        )

    data = resp.json()
    print(f"  Prediction: {data.get('prediction')}")
    print(f"  Confidence: {data.get('confidence')}%")
    assert resp.status_code == 200

    scores = supabase.table("rottenness_scores") \
        .select("*") \
        .eq("inventory_id", test_inventory_id) \
        .execute()

    assert len(scores.data) >= 1, "Score was not written to Supabase"
    score = scores.data[-1]
    print(f"  DB label:   {score['rotten_label']}")
    print(f"  DB mult:    {score['rotten_multiplier']}")
    print(f"  DB conf:    {score['confidence']}")
    print("  PASSED\n")


def test_classify_no_file():
    print("=" * 55)
    print("TEST 3: Classify with no file (expect 400)")
    print("=" * 55)

    resp = requests.post(f"{BASE_URL}/classify")
    print(f"  Status: {resp.status_code}")
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code}"
    print("  PASSED\n")


def test_read_inventory_with_scores():
    print("=" * 55)
    print("TEST 4: Read inventory includes new score")
    print("=" * 55)

    resp = requests.get(f"{BASE_URL}/inventory")
    assert resp.status_code == 200
    products = resp.json()

    test_product = next((p for p in products if p["id"] == test_inventory_id), None)
    assert test_product is not None, "Test product not found in inventory"
    assert test_product["rotten_label"] is not None, "Score not joined to inventory"

    print(f"  Product:    {test_product['product_name']}")
    print(f"  Label:      {test_product['rotten_label']}")
    print(f"  Multiplier: {test_product['rotten_multiplier']}")
    print("  PASSED\n")


def cleanup():
    print("=" * 55)
    print("CLEANUP: Removing test data")
    print("=" * 55)

    if test_inventory_id:
        supabase.table("rottenness_scores").delete().eq("inventory_id", test_inventory_id).execute()
        supabase.table("inventory").delete().eq("id", test_inventory_id).execute()
        print(f"  Deleted inventory row {test_inventory_id} and its scores")

    print("  DONE\n")


if __name__ == "__main__":
    wait_for_server()

    try:
        setup_test_inventory()
        test_classify_basic()
        test_classify_with_score()
        test_classify_no_file()
        test_read_inventory_with_scores()
        print("ALL TESTS PASSED")
    finally:
        cleanup()

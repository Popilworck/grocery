import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def get_all_inventory():
    result = supabase.table("inventory").select("*").execute()
    return result.data


def save_score(inventory_id, label, multiplier, confidence):
    supabase.table("rottenness_scores").insert({
        "inventory_id": inventory_id,
        "rotten_label": label,
        "rotten_multiplier": multiplier,
        "confidence": confidence
    }).execute()


if __name__ == "__main__":
    inventory = get_all_inventory()
    for item in inventory:
        # ML model goes here — replace the dummy values below
        label, multiplier, confidence = "fresh", 0.1, 0.95

        save_score(item["id"], label, multiplier, confidence)
        print(f"Scored {item['product_name']}: {label} ({multiplier})")

import os
import sys
import io
import base64
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS
from google import genai
from supabase import create_client
from dotenv import load_dotenv
from PIL import Image
import json
import traceback

load_dotenv()

app = Flask(__name__)
CORS(app)

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
MODEL_PATH = os.environ.get(
    "MODEL_PATH",
    str(Path(__file__).resolve().parent.parent / "ml" / "training_output_efficientnet" / "checkpoints" / "best_model.pth"),
)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# ── ML model (lazy-loaded) ──────────────────────────────────────────────────
_ml_model = None

STATUS_MAP = {"fresh": "good", "stale": "warning", "rotten": "bad"}

def _ml_available():
    """Check if the trained model checkpoint exists on disk."""
    return bool(MODEL_PATH) and Path(MODEL_PATH).exists()


def _get_ml_model():
    """Load the EfficientNet checkpoint once, return (model, device, img_size)."""
    global _ml_model
    if _ml_model is not None:
        return _ml_model

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ml"))
    from predict import load_model
    _ml_model = load_model(MODEL_PATH)
    return _ml_model


def _classify_with_model(image: Image.Image):
    """Classify using the trained EfficientNet model."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ml"))
    from predict import classify
    model, device, img_size = _get_ml_model()
    return classify(image, model, device, img_size)


def _classify_with_gemini(image: Image.Image):
    """Fallback: classify freshness using Gemini Vision when no local model is available."""
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    b64 = base64.standard_b64encode(buf.getvalue()).decode()

    prompt = (
        "You are a food freshness classifier. Look at this image and classify the food item. "
        "Return ONLY a JSON object with exactly these fields, no markdown, no explanation:\n"
        '{"prediction": "fresh" or "stale" or "rotten", "confidence": number 0-100, "rot_score": number 0.0-1.0}'
    )

    response = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            {"inline_data": {"mime_type": "image/png", "data": b64}},
            prompt,
        ],
    )

    raw = response.text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    result = json.loads(raw)
    return result["prediction"], float(result["confidence"]), float(result["rot_score"])

@app.route("/upload-csv", methods=["POST"])
def upload_csv():
    try:
        file = request.files["file"]
        csv_text = file.read().decode("utf-8")

        prompt = f"""You are a data parser. Convert this CSV into a JSON array that strictly matches this structure:
{{
  "product_name": string,
  "category": string,
  "quantity": integer,
  "unit": string,
  "date_received": "YYYY-MM-DD",
  "expiry_date": "YYYY-MM-DD",
  "batch_id": string
}}

Rules:
- Return ONLY a valid JSON array, no explanation, no markdown
- If a field is missing from the CSV, use null
- Dates must be in YYYY-MM-DD format

CSV:
{csv_text}"""

        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )

        # Strip markdown code blocks if Gemini wraps it
        raw = response.text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()

        parsed_data = json.loads(raw)
        valid = [row for row in parsed_data if row.get("product_name")]
        skipped = len(parsed_data) - len(valid)

        if valid:
            supabase.table("inventory").insert(valid).execute()

        return jsonify({
            "success": True,
            "rows_inserted": len(valid),
            "rows_skipped": skipped,
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/inventory", methods=["GET"])
def get_inventory_with_scores():
    result = supabase.table("inventory").select(
        "*, rottenness_scores(*)"
    ).execute()

    products = []
    for p in result.data:
        scores = p.get("rottenness_scores", [])
        latest = scores[-1] if scores else None
        products.append({
            "id": p["id"],
            "product_name": p["product_name"],
            "category": p.get("category"),
            "quantity": p.get("quantity"),
            "unit": p.get("unit"),
            "date_received": p.get("date_received"),
            "expiry_date": p.get("expiry_date"),
            "batch_id": p.get("batch_id"),
            "rotten_label": latest["rotten_label"] if latest else None,
            "rotten_multiplier": latest["rotten_multiplier"] if latest else None,
            "confidence": latest["confidence"] if latest else None,
        })

    return jsonify(products)


@app.route("/classify", methods=["POST"])
def classify_image():
    """Classify a food image for freshness. Uses the trained model if available, otherwise Gemini Vision."""
    try:
        if "file" not in request.files:
            return jsonify({"error": "No image file provided"}), 400

        file = request.files["file"]
        image = Image.open(file.stream).convert("RGB")
        inventory_id = request.form.get("inventory_id")

        if _ml_available():
            prediction, confidence, rot_score = _classify_with_model(image)
            method = "efficientnet"
        else:
            prediction, confidence, rot_score = _classify_with_gemini(image)
            method = "gemini-vision"

        status = STATUS_MAP.get(prediction, "unchecked")

        if inventory_id:
            supabase.table("rottenness_scores").insert({
                "inventory_id": int(inventory_id),
                "rotten_label": prediction,
                "rotten_multiplier": rot_score,
                "confidence": confidence,
            }).execute()

        return jsonify({
            "prediction": prediction,
            "confidence": round(confidence, 1),
            "rot_score": round(rot_score, 2),
            "status": status,
            "method": method,
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5001)

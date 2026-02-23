"""
Freshness Classifier — Detection + Inference
=============================================
Finds a food item in a larger image using template matching,
draws a bounding box coloured by freshness (green=fresh, red=rotten),
and prints the freshness prediction.

Usage:
    # Just classify a single image (no template matching):
    python predict.py --image ./tomato.jpg

    # Find item in a larger scene and classify it:
    python predict.py --image ./shelf.jpg --template ./tomato_crop.jpg

    # Custom model or output path:
    python predict.py --image ./shelf.jpg --template ./tomato_crop.jpg --output result.jpg --model ./training_output_efficientnet/checkpoints/best_model.pth

Output (always printed):
    prediction: stale
    confidence: 74.3%
    rot_score:  0.51
"""

import argparse
from pathlib import Path

import cv2
import torch
import torch.nn.functional as F
import timm
from torchvision import transforms
from PIL import Image

DEFAULT_MODEL = "./training_output_efficientnet/checkpoints/best_model.pth"

CLASS_NAMES = ["fresh", "rotten", "stale"]

ROT_WEIGHT = {
    "fresh":  0.0,
    "stale":  0.5,
    "rotten": 1.0,
}


# ─────────────────────────────────────────────────────────────────────────────
# COLOR
# ─────────────────────────────────────────────────────────────────────────────

def freshness_color(rot_score: float) -> tuple:
    """
    Maps rot_score (0.0=fresh, 1.0=rotten) to a BGR color.
    0.0 → green (0, 255, 0)
    0.5 → yellow (0, 255, 255)
    1.0 → red (0, 0, 255)
    """
    rot_score = max(0.0, min(1.0, rot_score))
    green = int(255 * (1.0 - rot_score))
    red   = int(255 * rot_score)
    return (0, green, red)


# ─────────────────────────────────────────────────────────────────────────────
# MODEL
# ─────────────────────────────────────────────────────────────────────────────

def load_model(model_path: str):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt   = torch.load(model_path, map_location=device)
    config = ckpt.get("config", {})

    model = timm.create_model("efficientnet_b4", pretrained=False, num_classes=3)
    model.load_state_dict(ckpt["model"])
    model.to(device)
    model.eval()
    return model, device, config.get("img_size", 380)


# ─────────────────────────────────────────────────────────────────────────────
# FRESHNESS INFERENCE
# ─────────────────────────────────────────────────────────────────────────────

def classify(image: Image.Image, model, device, img_size: int):
    """Run freshness classification on a PIL image."""
    transform = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406],
                             std=[0.229, 0.224, 0.225]),
    ])

    tensor = transform(image).unsqueeze(0).to(device)

    with torch.no_grad():
        probs = F.softmax(model(tensor), dim=1)[0]

    scores     = {CLASS_NAMES[i]: float(probs[i]) for i in range(3)}
    prediction = max(scores, key=scores.get)
    confidence = scores[prediction] * 100
    rot_score  = sum(scores[cls] * ROT_WEIGHT[cls] for cls in CLASS_NAMES)

    return prediction, confidence, rot_score


# ─────────────────────────────────────────────────────────────────────────────
# TEMPLATE MATCHING + DRAW BOX
# ─────────────────────────────────────────────────────────────────────────────

def find_and_draw_box(
    main_image_path: str,
    template_path: str,
    output_path: str,
    rot_score: float,
    prediction: str,
    confidence: float,
):
    """
    Finds template in main image, draws a freshness-coloured bounding box,
    and overlays the prediction label.
    """
    main_img     = cv2.imread(main_image_path)
    template_img = cv2.imread(template_path)

    if main_img is None or template_img is None:
        print("Error: could not load images for template matching.")
        return

    main_gray     = cv2.cvtColor(main_img, cv2.COLOR_BGR2GRAY)
    template_gray = cv2.cvtColor(template_img, cv2.COLOR_BGR2GRAY)

    h, w = template_gray.shape

    result = cv2.matchTemplate(main_gray, template_gray, cv2.TM_CCOEFF_NORMED)
    _, match_confidence, _, max_loc = cv2.minMaxLoc(result)

    top_left     = max_loc
    bottom_right = (top_left[0] + w, top_left[1] + h)
    color        = freshness_color(rot_score)

    # Draw bounding box
    cv2.rectangle(main_img, top_left, bottom_right, color, 3)

    # Draw label above the box
    label = f"{prediction} {confidence:.1f}%"
    label_pos = (top_left[0], max(top_left[1] - 10, 20))
    cv2.putText(
        main_img, label, label_pos,
        cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2, cv2.LINE_AA
    )

    cv2.imwrite(output_path, main_img)
    print(f"Saved annotated image to: {output_path}")
    print(f"Template match confidence: {match_confidence:.2f}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image",    required=True,         help="Main image (or cropped item if no template)")
    parser.add_argument("--template", default=None,          help="Cropped template to locate in --image")
    parser.add_argument("--output",   default="output.jpg",  help="Output path for annotated image")
    parser.add_argument("--model",    default=DEFAULT_MODEL, help="Path to model checkpoint")
    args = parser.parse_args()

    if not Path(args.image).exists():
        print(f"Error: image not found at {args.image}")
        return
    if not Path(args.model).exists():
        print(f"Error: checkpoint not found at {args.model}")
        return

    model, device, img_size = load_model(args.model)

    # Classify either the template crop (if provided) or the full image
    classify_path = args.template if args.template else args.image
    image         = Image.open(classify_path).convert("RGB")
    prediction, confidence, rot_score = classify(image, model, device, img_size)

    # Always print results
    print(f"prediction: {prediction}")
    print(f"confidence: {confidence:.1f}%")
    print(f"rot_score:  {rot_score:.2f}")

    # Draw box only if template matching is requested
    if args.template:
        if not Path(args.template).exists():
            print(f"Error: template not found at {args.template}")
            return
        find_and_draw_box(
            args.image, args.template, args.output,
            rot_score, prediction, confidence
        )


if __name__ == "__main__":
    main()
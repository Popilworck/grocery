
import argparse
from pathlib import Path

import cv2
import torch
import torch.nn.functional as F
import timm
from torchvision import transforms
from PIL import Image

DEFAULT_MODEL = "./training_output_efficientnet/checkpoints/best_model.pth"
CLASS_NAMES   = ["fresh", "rotten", "stale"]
ROT_WEIGHT    = {"fresh": 0.0, "stale": 0.5, "rotten": 1.0}

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

# Scene image filename — skip this when iterating crops
SCENE_FILENAMES = {
    "produce-aisle-grocery-store-pic(1).jpg"
}


def freshness_color(rot_score: float) -> tuple:
    """0.0=green, 0.5=yellow, 1.0=red (BGR)"""
    rot_score = max(0.0, min(1.0, rot_score))
    green = int(255 * (1.0 - rot_score))
    red   = int(255 * rot_score)
    return (0, green, red)


def load_model(model_path: str):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt   = torch.load(model_path, map_location=device)
    config = ckpt.get("config", {})
    model  = timm.create_model("efficientnet_b4", pretrained=False, num_classes=3)
    model.load_state_dict(ckpt["model"])
    model.to(device)
    model.eval()
    return model, device, config.get("img_size", 380)


def classify(crop_path: Path, model, device, img_size: int):
    transform = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406],
                             std=[0.229, 0.224, 0.225]),
    ])
    image  = Image.open(crop_path).convert("RGB")
    tensor = transform(image).unsqueeze(0).to(device)

    with torch.no_grad():
        probs = F.softmax(model(tensor), dim=1)[0]

    scores     = {CLASS_NAMES[i]: float(probs[i]) for i in range(3)}
    prediction = max(scores, key=scores.get)
    confidence = scores[prediction] * 100
    rot_score  = sum(scores[cls] * ROT_WEIGHT[cls] for cls in CLASS_NAMES)
    return prediction, confidence, rot_score


def find_crop_in_scene(scene_gray, crop_path: Path):
    """Returns (top_left, bottom_right) of best match, or None if crop can't be loaded."""
    crop = cv2.imread(str(crop_path))
    if crop is None:
        return None, None

    crop_gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    h, w      = crop_gray.shape

    # Skip if crop is larger than scene
    sh, sw = scene_gray.shape
    if h > sh or w > sw:
        return None, None

    result   = cv2.matchTemplate(scene_gray, crop_gray, cv2.TM_CCOEFF_NORMED)
    _, _, _, loc = cv2.minMaxLoc(result)

    top_left     = loc
    bottom_right = (top_left[0] + w, top_left[1] + h)
    return top_left, bottom_right


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--crops",  required=True,         help="Folder containing cropped vegetable images")
    parser.add_argument("--scene",  required=True,         help="Full scene/shelf image")
    parser.add_argument("--output", default="output.jpg",  help="Output path for annotated image")
    parser.add_argument("--model",  default=DEFAULT_MODEL, help="Path to model checkpoint")
    args = parser.parse_args()

    crops_dir = Path(args.crops)
    if not crops_dir.is_dir():
        print(f"Error: crops folder not found: {args.crops}")
        return
    if not Path(args.scene).exists():
        print(f"Error: scene image not found: {args.scene}")
        return
    if not Path(args.model).exists():
        print(f"Error: model checkpoint not found: {args.model}")
        return

    # Load model
    model, device, img_size = load_model(args.model)

    # Load scene
    scene = cv2.imread(args.scene)
    if scene is None:
        print(f"Error: could not load scene image: {args.scene}")
        return
    scene_gray = cv2.cvtColor(scene, cv2.COLOR_BGR2GRAY)

    # Get all crop images, excluding the scene itself
    scene_name = Path(args.scene).name.lower()
    crop_paths = [
        p for p in sorted(crops_dir.iterdir())
        if p.suffix.lower() in IMAGE_EXTENSIONS
        and p.name.lower() != scene_name
        and p.name.lower() not in SCENE_FILENAMES
    ]

    print(f"\nFound {len(crop_paths)} crop images. Processing...\n")

    for crop_path in crop_paths:
        prediction, confidence, rot_score = classify(crop_path, model, device, img_size)
        top_left, bottom_right            = find_crop_in_scene(scene_gray, crop_path)

        print(f"{crop_path.name}")
        print(f"  prediction: {prediction}  confidence: {confidence:.1f}%  rot_score: {rot_score:.2f}")

        if top_left is None:
            print(f"  skipped (could not load or match)")
            continue

        color = freshness_color(rot_score)
        cv2.rectangle(scene, top_left, bottom_right, color, 3)

    cv2.imwrite(args.output, scene)
    print(f"\nSaved annotated scene to: {args.output}")


if __name__ == "__main__":
    main()
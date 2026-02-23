"""
Freshness Classifier
=====================
Takes a cropped image of a food item and a full scene image.
Finds the crop in the scene, classifies its freshness,
and draws a coloured bounding box on the scene.

Install:
    pip install torch torchvision timm opencv-python-headless Pillow

Usage:
    python predict.py --crop ./tomato_crop.jpg --scene ./shelf.jpg
    python predict.py --crop ./tomato_crop.jpg --scene ./shelf.jpg --output result.jpg --model ./training_output_efficientnet/checkpoints/best_model.pth

Output:
    prediction: stale
    confidence: 74.3%
    rot_score:  0.51
    Saved result to: result.jpg
"""

import argparse
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn.functional as F
import timm
from torchvision import transforms
from PIL import Image

DEFAULT_MODEL = "./training_output_efficientnet/checkpoints/best_model.pth"
CLASS_NAMES   = ["fresh", "rotten", "stale"]
ROT_WEIGHT    = {"fresh": 0.0, "stale": 0.5, "rotten": 1.0}


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


def classify(crop_path: str, model, device, img_size: int):
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


def find_and_annotate(scene_path: str, crop_path: str, output_path: str,
                      prediction: str, confidence: float, rot_score: float):
    scene = cv2.imread(scene_path)
    crop  = cv2.imread(crop_path)

    if scene is None:
        print(f"Error: could not load scene image: {scene_path}")
        return
    if crop is None:
        print(f"Error: could not load crop image: {crop_path}")
        return

    scene_gray = cv2.cvtColor(scene, cv2.COLOR_BGR2GRAY)
    crop_gray  = cv2.cvtColor(crop,  cv2.COLOR_BGR2GRAY)

    h, w = crop_gray.shape

    result               = cv2.matchTemplate(scene_gray, crop_gray, cv2.TM_CCOEFF_NORMED)
    _, match_val, _, loc = cv2.minMaxLoc(result)

    top_left     = loc
    bottom_right = (top_left[0] + w, top_left[1] + h)
    color        = freshness_color(rot_score)

    cv2.rectangle(scene, top_left, bottom_right, color, 3)


    cv2.imwrite(output_path, scene)
    print(f"match confidence: {match_val:.2f}")
    print(f"saved result to:  {output_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--crop",   required=True,         help="Cropped image of the food item")
    parser.add_argument("--scene",  required=True,         help="Full scene image to locate the item in")
    parser.add_argument("--output", default="output.jpg",  help="Output path for annotated image")
    parser.add_argument("--model",  default=DEFAULT_MODEL, help="Path to model checkpoint")
    args = parser.parse_args()

    for path, name in [(args.crop, "crop"), (args.scene, "scene"), (args.model, "model")]:
        if not Path(path).exists():
            print(f"Error: {name} not found at {path}")
            return

    model, device, img_size       = load_model(args.model)
    prediction, confidence, rot_score = classify(args.crop, model, device, img_size)

    print(f"prediction: {prediction}")
    print(f"confidence: {confidence:.1f}%")
    print(f"rot_score:  {rot_score:.2f}")

    find_and_annotate(args.scene, args.crop, args.output,
                      prediction, confidence, rot_score)


if __name__ == "__main__":
    main()
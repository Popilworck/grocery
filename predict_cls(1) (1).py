import argparse, json
from pathlib import Path
from PIL import Image
import torch
import torch.nn as nn
from torchvision import transforms, models

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

def _model(arch, k):
    arch = arch.lower()
    
    # ConvNeXt Family
    if arch == "convnext_tiny":
        m = models.convnext_tiny(weights=None)
        m.classifier[-1] = nn.Linear(m.classifier[-1].in_features, k)
        return m
    if arch == "convnext_base":
        m = models.convnext_base(weights=None)
        m.classifier[-1] = nn.Linear(m.classifier[-1].in_features, k)
        return m
        
    # EfficientNet
    if arch == "efficientnet_v2_s":
        m = models.efficientnet_v2_s(weights=None)
        m.classifier[-1] = nn.Linear(m.classifier[-1].in_features, k)
        return m
        
    # ResNet Family
    if arch == "resnet50":
        m = models.resnet50(weights=None)
        m.fc = nn.Linear(m.fc.in_features, k)
        return m
        
    # Vision Transformer (ViT)
    if arch == "vit_b_16":
        m = models.vit_b_16(weights=None)
        m.heads.head = nn.Linear(m.heads.head.in_features, k)
        return m

    raise ValueError(f"Unknown arch: {arch}. Available: convnext_tiny, convnext_base, efficientnet_v2_s, resnet50, vit_b_16")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--class_to_idx", required=True)
    ap.add_argument("--arch", default="convnext_tiny")
    ap.add_argument("--img_size", type=int, default=224)
    ap.add_argument("--input", required=True)
    ap.add_argument("--glob", default="*.jpg")
    ap.add_argument("--topk", type=int, default=3)
    args = ap.parse_args()

    with open(args.class_to_idx) as f:
        c2i = json.load(f)
    i2c = {v: k for k, v in c2i.items()}
    k = len(i2c)

    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    m = _model(args.arch, k).to(dev).eval()

    ck = torch.load(args.ckpt, map_location="cpu")
    sd = ck["model"] if isinstance(ck, dict) and "model" in ck else ck
    m.load_state_dict(sd, strict=True)

    tf = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(args.img_size),
        transforms.ToTensor(),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ])

    inp = Path(args.input)
    if inp.is_dir():
        pics = sorted(inp.rglob(args.glob))
    else:
        pics = [inp]

    for p in pics:
        im = Image.open(p).convert("RGB")
        x = tf(im).unsqueeze(0).to(dev)
        with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16, enabled=(dev.type == "cuda")):
            logits = m(x)[0]
            probs = torch.softmax(logits, dim=0)
        top = torch.topk(probs, k=min(args.topk, probs.numel()))
        out = []
        for score, idx in zip(top.values.tolist(), top.indices.tolist()):
            out.append((i2c[idx], float(score)))
        print(str(p), out)

if __name__ == "__main__":
    main()
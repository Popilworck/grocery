import argparse, json
from pathlib import Path

import numpy as np
import cv2
from PIL import Image
import torch
import torch.nn as nn
from torchvision import transforms, models
from tqdm import tqdm
from pycocotools import mask as mask_utils
from segment_anything import sam_model_registry, SamAutomaticMaskGenerator

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


def _load_cls(arch, ckpt_path, class_to_idx_path, img_size=224):
    with open(class_to_idx_path) as f:
        c2i = json.load(f)
    i2c = {v: k for k, v in c2i.items()}
    k = len(i2c)

    def build():
        a = arch.lower()
        if a == "convnext_tiny":
            m = models.convnext_tiny(weights=None)
            m.classifier[-1] = nn.Linear(m.classifier[-1].in_features, k)
            return m
        if a == "convnext_base":
            m = models.convnext_base(weights=None)
            m.classifier[-1] = nn.Linear(m.classifier[-1].in_features, k)
            return m
        if a == "efficientnet_v2_s":
            m = models.efficientnet_v2_s(weights=None)
            m.classifier[-1] = nn.Linear(m.classifier[-1].in_features, k)
            return m
        raise ValueError(a)

    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    m = build().to(dev).eval()
    ck = torch.load(ckpt_path, map_location="cpu")
    sd = ck["model"] if isinstance(ck, dict) and "model" in ck else ck
    m.load_state_dict(sd, strict=True)

    tf = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(img_size),
        transforms.ToTensor(),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ])
    return m, tf, dev, i2c


def _mask_filters(h, w, m):
    area = float(m.get("area", 0.0))
    if area <= 0:
        return False

    frac = area / float(h * w)
    if frac < 0.003:
        return False
    if frac > 0.25:
        return False

    x, y, bw, bh = m["bbox"]
    bw, bh = float(bw), float(bh)
    if bw < 32 or bh < 32:
        return False

    ar = max(bw / bh, bh / bw)
    if ar > 4.0:
        return False

    st = float(m.get("stability_score", 1.0))
    if st < 0.92:
        return False

    return True


def _nms_masks(masks, iou_thr=0.85):
    keep = []
    order = sorted(range(len(masks)), key=lambda i: float(masks[i].get("predicted_iou", 0.0)), reverse=True)

    def iou(a, b):
        aa = a["segmentation"]
        bb = b["segmentation"]
        inter = np.logical_and(aa, bb).sum()
        uni = np.logical_or(aa, bb).sum()
        return float(inter) / float(uni + 1e-9)

    for i in order:
        ok = True
        for j in keep:
            if iou(masks[i], masks[j]) >= iou_thr:
                ok = False
                break
        if ok:
            keep.append(i)
    return [masks[i] for i in keep]


def _rle_from_bool(mask_bool):
    mb = np.asfortranarray(mask_bool.astype(np.uint8))
    rle = mask_utils.encode(mb)
    rle["counts"] = rle["counts"].decode("ascii")
    return rle


def _bbox_xywh_from_mask(mask_bool):
    ys, xs = np.where(mask_bool)
    if len(xs) == 0:
        return None
    x1 = int(xs.min())
    x2 = int(xs.max())
    y1 = int(ys.min())
    y2 = int(ys.max())
    w = x2 - x1 + 1
    h = y2 - y1 + 1
    return [x1, y1, w, h]


def _bbox_corners_from_xywh(bb):
    x, y, w, h = bb
    return int(x), int(y), int(x + w), int(y + h)


def _crop_and_alpha(img_bgr, mask_bool, pad=8):
    H, W = mask_bool.shape
    bb_xywh = _bbox_xywh_from_mask(mask_bool)
    if bb_xywh is None:
        return None, None, None, None
    x1, y1, x2, y2 = _bbox_corners_from_xywh(bb_xywh)

    x1p = max(0, x1 - pad)
    y1p = max(0, y1 - pad)
    x2p = min(W, x2 + pad)
    y2p = min(H, y2 + pad)

    crop = img_bgr[y1p:y2p, x1p:x2p].copy()
    m = mask_bool[y1p:y2p, x1p:x2p]
    rgba = cv2.cvtColor(crop, cv2.COLOR_BGR2BGRA)
    rgba[..., 3] = (m.astype(np.uint8) * 255)
    return bb_xywh, (x1p, y1p, x2p, y2p), crop, rgba


def _cls_on_crop(model, tf, dev, crop_bgr, i2c):
    im = Image.fromarray(cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB))
    x = tf(im).unsqueeze(0).to(dev)
    with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16, enabled=(dev.type == "cuda")):
        logits = model(x)[0]
        probs = torch.softmax(logits, dim=0)
    top2 = torch.topk(probs, k=2)
    p1 = float(top2.values[0].item())
    p2 = float(top2.values[1].item())
    idx1 = int(top2.indices[0].item())
    return i2c[idx1], p1, (p1 - p2)


def _save_mask_png(mask_bool, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    m = (mask_bool.astype(np.uint8) * 255)
    cv2.imwrite(str(path), m)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images_dir", required=True)
    ap.add_argument("--out_dir", required=True)
    ap.add_argument("--sam_ckpt", required=True)
    ap.add_argument("--sam_type", default="vit_h", choices=["vit_h", "vit_l", "vit_b"])
    ap.add_argument("--cls_ckpt", required=True)
    ap.add_argument("--class_to_idx", required=True)
    ap.add_argument("--cls_arch", default="convnext_tiny")
    ap.add_argument("--cls_img_size", type=int, default=224)
    ap.add_argument("--min_cls_conf", type=float, default=0.60)
    ap.add_argument("--max_masks_per_image", type=int, default=120)
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()

    out = Path(args.out_dir)
    (out / "crops").mkdir(parents=True, exist_ok=True)
    (out / "masks").mkdir(parents=True, exist_ok=True)
    (out / "debug").mkdir(parents=True, exist_ok=True)

    cls_m, cls_tf, dev, i2c = _load_cls(args.cls_arch, args.cls_ckpt, args.class_to_idx, args.cls_img_size)
    classes = [i2c[i] for i in range(len(i2c))]
    cat_to_id = {c: i + 1 for i, c in enumerate(classes)}

    sam = sam_model_registry[args.sam_type](checkpoint=args.sam_ckpt)
    sam.to(device=dev if dev.type == "cuda" else "cpu")
    gen = SamAutomaticMaskGenerator(
        sam,
        points_per_side=16,
        pred_iou_thresh=0.92,
        stability_score_thresh=0.92,
        crop_n_layers=0,
        min_mask_region_area=600,
    )

    exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    imgs = sorted([p for p in Path(args.images_dir).rglob("*") if p.suffix.lower() in exts])

    coco = {"images": [], "annotations": [], "categories": []}
    for name, cid in cat_to_id.items():
        coco["categories"].append({"id": cid, "name": name, "supercategory": "produce"})

    ann_id = 1
    img_id = 1

    for p in tqdm(imgs, desc="images"):
        bgr = cv2.imread(str(p), cv2.IMREAD_COLOR)
        if bgr is None:
            continue
        H, W = bgr.shape[:2]
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

        ms = gen.generate(rgb)
        ms = [m for m in ms if _mask_filters(H, W, m)]
        ms = _nms_masks(ms, iou_thr=0.85)
        ms = ms[: min(60, args.max_masks_per_image)]

        coco["images"].append({
            "id": img_id,
            "file_name": str(p.relative_to(args.images_dir)).replace("\\", "/"),
            "width": W,
            "height": H,
        })

        dbg = bgr.copy() if args.debug else None

        for m in ms:
            mask_bool = m["segmentation"].astype(bool)

            pad_amount = int(max(mask_bool.shape) * 0.15)
            bb_xywh, bb_xyxy_padded, crop_bgr, rgba = _crop_and_alpha(bgr, mask_bool, pad=max(30, pad_amount))
            if bb_xywh is None:
                continue

            label, conf, margin = _cls_on_crop(cls_m, cls_tf, dev, crop_bgr, i2c)

            x, y, bw, bh = bb_xywh
            if bh <= 0:
                continue
            ar = float(bw) / float(bh)

            round_veggies = {"Broccoli", "Cabbage", "Capsicum", "Cauliflower", "Potato", "Pumpkin", "Tomato"}
            oval_veggies = {"Brinjal", "Papaya"}
            elongated = {"Bean", "Bitter_Gourd", "Bottle_Gourd", "Carrot", "Cucumber", "Radish"}

            if label in round_veggies and (ar < 0.33 or ar > 3.0):
                continue
            if label in oval_veggies and (ar < 0.25 or ar > 4.0):
                continue
            if label in elongated and (ar < 0.15 or ar > 6.0):
                continue

            if conf < args.min_cls_conf:
                continue
            if margin < 0.20:
                continue

            frac_bb = (float(bw) * float(bh)) / float(W * H)
            if frac_bb > 0.18:
                continue

            rle = _rle_from_bool(mask_bool)
            area = float(mask_utils.area(rle))
            bbox_xywh = [float(v) for v in bb_xywh]

            crop_name = f"{img_id:06d}_{ann_id:08d}_{label}.png"
            mask_name = f"{img_id:06d}_{ann_id:08d}_{label}_mask.png"

            cv2.imwrite(str(out / "crops" / crop_name), rgba)
            _save_mask_png(mask_bool, out / "masks" / mask_name)

            coco["annotations"].append({
                "id": ann_id,
                "image_id": img_id,
                "category_id": cat_to_id[label],
                "segmentation": rle,
                "area": area,
                "bbox": bbox_xywh,
                "iscrowd": 0,
                "score": float(conf),
                "crop_file": f"crops/{crop_name}",
                "mask_file": f"masks/{mask_name}",
            })

            if dbg is not None:
                x1p, y1p, x2p, y2p = bb_xyxy_padded
                cv2.rectangle(dbg, (x1p, y1p), (x2p, y2p), (0, 255, 0), 2)
                cv2.putText(
                    dbg,
                    f"{label}:{conf:.2f}",
                    (x1p, max(0, y1p - 5)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2,
                )

            ann_id += 1

        if dbg is not None:
            rel = str(p.relative_to(args.images_dir)).replace("\\", "_").replace("/", "_")
            cv2.imwrite(str(out / "debug" / f"{img_id:06d}_{rel}.jpg"), dbg)

        img_id += 1

    with open(out / "instances.json", "w") as f:
        json.dump(coco, f)

    print("wrote:", str(out / "instances.json"))
    print("crops:", str(out / "crops"))
    print("masks:", str(out / "masks"))


if __name__ == "__main__":
    main()
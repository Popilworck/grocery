import argparse
import json
import time
from dataclasses import dataclass
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import datasets, transforms, models

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


def build_transforms(img_size: int):
    train_tf = transforms.Compose([
        transforms.RandomResizedCrop(img_size, scale=(0.25, 1.0), ratio=(0.6, 1.6)),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomRotation(degrees=15),
        transforms.ColorJitter(0.4, 0.4, 0.4, 0.15),
        transforms.ToTensor(),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ])

    val_tf = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(img_size),
        transforms.ToTensor(),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ])

    return train_tf, val_tf


def build_dataloaders(train_dir: str, val_dir: str, img_size: int, batch_size: int, num_workers: int):
    train_tf, val_tf = build_transforms(img_size)

    train_ds = datasets.ImageFolder(train_dir, transform=train_tf)
    val_ds = datasets.ImageFolder(val_dir, transform=val_tf)

    train_loader = DataLoader(
        train_ds,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=True,
        persistent_workers=(num_workers > 0),
        drop_last=True,
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=True,
        persistent_workers=(num_workers > 0),
        drop_last=False,
    )
    return train_ds, val_ds, train_loader, val_loader


def build_model(arch: str, num_classes: int):
    a = arch.lower()

    if a == "convnext_tiny":
        m = models.convnext_tiny(weights=models.ConvNeXt_Tiny_Weights.IMAGENET1K_V1)
        m.classifier[-1] = nn.Linear(m.classifier[-1].in_features, num_classes)
        return m

    if a == "convnext_base":
        m = models.convnext_base(weights=models.ConvNeXt_Base_Weights.IMAGENET1K_V1)
        m.classifier[-1] = nn.Linear(m.classifier[-1].in_features, num_classes)
        return m

    if a == "efficientnet_v2_s":
        m = models.efficientnet_v2_s(weights=models.EfficientNet_V2_S_Weights.IMAGENET1K_V1)
        m.classifier[-1] = nn.Linear(m.classifier[-1].in_features, num_classes)
        return m

    if a == "resnet50":
        m = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V1)
        m.fc = nn.Linear(m.fc.in_features, num_classes)
        return m

    if a == "vit_b_16":
        m = models.vit_b_16(weights=models.ViT_B_16_Weights.IMAGENET1K_V1)
        m.heads.head = nn.Linear(m.heads.head.in_features, num_classes)
        return m

    raise ValueError(f"Unknown arch: {arch}")


def accuracy_top1(logits: torch.Tensor, targets: torch.Tensor) -> float:
    return (logits.argmax(dim=1) == targets).float().mean().item()


@dataclass
class RunStats:
    loss: float = 0.0
    acc: float = 0.0
    n: int = 0

    def update(self, loss_val: float, acc_val: float, batch_size: int):
        self.loss += loss_val * batch_size
        self.acc += acc_val * batch_size
        self.n += batch_size

    def mean(self):
        if self.n == 0:
            return 0.0, 0.0
        return self.loss / self.n, self.acc / self.n


def get_autocast_dtype(amp: str):
    s = amp.lower()
    if s == "bf16":
        return torch.bfloat16
    if s == "fp16":
        return torch.float16
    if s == "none":
        return None
    raise ValueError("amp must be bf16, fp16, or none")


def save_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=2)


def train_one_epoch(model, loader, criterion, optimizer, device, amp_dtype, grad_clip):
    model.train()
    stats = RunStats()
    scaler = torch.cuda.amp.GradScaler() if (device.type == "cuda" and amp_dtype == torch.float16) else None

    for images, targets in loader:
        images = images.to(device, non_blocking=True)
        targets = targets.to(device, non_blocking=True)

        optimizer.zero_grad(set_to_none=True)

        if amp_dtype is None or device.type != "cuda":
            logits = model(images)
            loss = criterion(logits, targets)
            loss.backward()
            if grad_clip > 0:
                nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
            optimizer.step()
        else:
            with torch.autocast(device_type="cuda", dtype=amp_dtype):
                logits = model(images)
                loss = criterion(logits, targets)

            if scaler is not None:
                scaler.scale(loss).backward()
                if grad_clip > 0:
                    scaler.unscale_(optimizer)
                    nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
                scaler.step(optimizer)
                scaler.update()
            else:
                loss.backward()
                if grad_clip > 0:
                    nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
                optimizer.step()

        acc = accuracy_top1(logits.detach(), targets)
        stats.update(loss.item(), acc, images.size(0))

    return stats.mean()


@torch.no_grad()
def eval_one_epoch(model, loader, criterion, device, amp_dtype):
    model.eval()
    stats = RunStats()

    for images, targets in loader:
        images = images.to(device, non_blocking=True)
        targets = targets.to(device, non_blocking=True)

        if amp_dtype is None or device.type != "cuda":
            logits = model(images)
            loss = criterion(logits, targets)
        else:
            with torch.autocast(device_type="cuda", dtype=amp_dtype):
                logits = model(images)
                loss = criterion(logits, targets)

        acc = accuracy_top1(logits, targets)
        stats.update(loss.item(), acc, images.size(0))

    return stats.mean()


class WarmupCosine:
    def __init__(self, optimizer, warmup_epochs, total_epochs, min_lr=0.0):
        self.opt = optimizer
        self.warm = max(0, int(warmup_epochs))
        self.total = int(total_epochs)
        self.min_lr = float(min_lr)
        self.base_lrs = [g["lr"] for g in optimizer.param_groups]
        self.epoch = 0

    def step(self):
        self.epoch += 1
        t = self.epoch

        if self.warm > 0 and t <= self.warm:
            w = t / self.warm
            for g, b in zip(self.opt.param_groups, self.base_lrs):
                g["lr"] = b * w
            return

        tt = (t - self.warm) / max(1, (self.total - self.warm))
        c = 0.5 * (1.0 + torch.cos(torch.tensor(tt * 3.1415926535))).item()
        for g, b in zip(self.opt.param_groups, self.base_lrs):
            g["lr"] = self.min_lr + (b - self.min_lr) * c


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--train_dir", type=str, required=True)
    p.add_argument("--val_dir", type=str, required=True)
    p.add_argument("--arch", type=str, default="convnext_base")
    p.add_argument("--img_size", type=int, default=224)
    p.add_argument("--batch_size", type=int, default=256)
    p.add_argument("--epochs", type=int, default=30)
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--weight_decay", type=float, default=0.05)
    p.add_argument("--label_smoothing", type=float, default=0.1)
    p.add_argument("--num_workers", type=int, default=12)
    p.add_argument("--amp", type=str, default="bf16", choices=["bf16", "fp16", "none"])
    p.add_argument("--grad_clip", type=float, default=0.0)
    p.add_argument("--warmup_epochs", type=int, default=2)
    p.add_argument("--out_dir", type=str, required=True)
    p.add_argument("--seed", type=int, default=1337)
    args = p.parse_args()

    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)
    torch.backends.cudnn.benchmark = True

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    amp_dtype = get_autocast_dtype(args.amp)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    train_ds, val_ds, train_loader, val_loader = build_dataloaders(
        args.train_dir, args.val_dir, args.img_size, args.batch_size, args.num_workers
    )

    if set(train_ds.classes) != set(val_ds.classes):
        raise RuntimeError("Train/val class folders differ. Ensure identical class names in both.")

    save_json(out_dir / "classes.json", train_ds.classes)
    save_json(out_dir / "class_to_idx.json", train_ds.class_to_idx)
    save_json(out_dir / "run_args.json", vars(args))

    num_classes = len(train_ds.classes)
    model = build_model(args.arch, num_classes).to(device)

    criterion = nn.CrossEntropyLoss(label_smoothing=args.label_smoothing)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    scheduler = WarmupCosine(optimizer, warmup_epochs=args.warmup_epochs, total_epochs=args.epochs, min_lr=args.lr * 0.05)

    best_val_acc = -1.0
    metrics_path = out_dir / "metrics.jsonl"

    for epoch in range(1, args.epochs + 1):
        t0 = time.time()

        train_loss, train_acc = train_one_epoch(
            model, train_loader, criterion, optimizer, device, amp_dtype, args.grad_clip
        )
        val_loss, val_acc = eval_one_epoch(model, val_loader, criterion, device, amp_dtype)

        scheduler.step()

        dt = time.time() - t0
        row = {
            "epoch": epoch,
            "train_loss": train_loss,
            "train_acc": train_acc,
            "val_loss": val_loss,
            "val_acc": val_acc,
            "sec": dt,
            "lr": optimizer.param_groups[0]["lr"],
        }

        with open(metrics_path, "a") as f:
            f.write(json.dumps(row) + "\n")

        ckpt_last = {
            "epoch": epoch,
            "model": model.state_dict(),
            "optimizer": optimizer.state_dict(),
            "best_val_acc": best_val_acc,
            "classes": train_ds.classes,
            "class_to_idx": train_ds.class_to_idx,
            "arch": args.arch,
            "img_size": args.img_size,
        }
        torch.save(ckpt_last, out_dir / "last.pt")

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            ckpt_best = dict(ckpt_last)
            ckpt_best["best_val_acc"] = best_val_acc
            torch.save(ckpt_best, out_dir / "best.pt")

        print(
            f"epoch {epoch:03d}/{args.epochs} | "
            f"train loss {train_loss:.4f} acc {train_acc:.4f} | "
            f"val loss {val_loss:.4f} acc {val_acc:.4f} | "
            f"{dt:.1f}s | lr {optimizer.param_groups[0]['lr']:.2e} | best {best_val_acc:.4f}"
        )

    print(f"done. best val acc = {best_val_acc:.4f}")
    print(f"artifacts in: {out_dir.resolve()}")


if __name__ == "__main__":
    main()
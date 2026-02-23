
import shutil
import random
from pathlib import Path
from collections import defaultdict

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURE THESE — change to match your actual paths
# ─────────────────────────────────────────────────────────────────────────────
RAW_DATA_ROOT = "."    # folder that contains potdar/, ulnn/, alinesellwia/
OUTPUT_ROOT   = "./merged_dataset"

TRAIN_RATIO = 0.80
VAL_RATIO   = 0.10
TEST_RATIO  = 0.10   # remainder

SEED = 42
# ─────────────────────────────────────────────────────────────────────────────

random.seed(SEED)

CLASS_NAMES      = {0: "fresh", 1: "stale", 2: "rotten"}
VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def is_image(path: Path) -> bool:
    return path.suffix.lower() in VALID_EXTENSIONS



POTDAR_PREFIX_MAP = {
    "fresh_": 0,
    "stale_": 1,
}

def collect_potdar(root: Path) -> list[tuple[Path, int]]:
    samples = []
    dataset_path = root / "potdar"
    if not dataset_path.exists():
        print(f"  [WARN] potdar/ not found at {dataset_path}, skipping.")
        return samples

    for folder in sorted(dataset_path.iterdir()):
        if not folder.is_dir():
            continue  # skips ImageLabels.txt etc.
        label = None
        for prefix, class_id in POTDAR_PREFIX_MAP.items():
            if folder.name.lower().startswith(prefix):
                label = class_id
                break
        if label is None:
            continue  # silently skip anything unrecognized
        for img in folder.rglob("*"):
            if is_image(img):
                samples.append((img, label))

    print(f"  Potdar:       {len(samples):,} images")
    return samples



ULNN_TOPLEVEL_MAP = {
    "fresh":  0,
    "rotten": 2,
}

def collect_ulnn(root: Path) -> list[tuple[Path, int]]:
    samples = []
    dataset_path = root / "ulnn" / "Dataset"
    if not dataset_path.exists():
        print(f"  [WARN] ulnn/Dataset/ not found at {dataset_path}, skipping.")
        return samples

    for top_folder in sorted(dataset_path.iterdir()):
        if not top_folder.is_dir():
            continue
        label = ULNN_TOPLEVEL_MAP.get(top_folder.name.lower())
        if label is None:
            print(f"  [WARN] ULNN: unrecognized folder '{top_folder.name}', skipping.")
            continue
        # One level deeper: Fresh/ -> FreshApple/ -> images
        for sub_folder in sorted(top_folder.iterdir()):
            if not sub_folder.is_dir():
                continue
            for img in sub_folder.rglob("*"):
                if is_image(img):
                    samples.append((img, label))

    print(f"  ULNN:         {len(samples):,} images")
    return samples



ALINESELLWIA_FOLDER_MAP = {
    # jeruk = orange
    "jeruk_segar":         0,
    "jeruk_segar_sedang":  1,
    "jeruk_busuk":         2,
    # tomat = tomato
    "tomat_segar":         0,
    "tomat_segar_sedang":  1,
    "tomat_busuk":         2,
    # wortel = carrot
    "wortel_segar":        0,
    "wortel_segar_sedang": 1,
    "wortel_busuk":        2,
}

def normalize_folder_name(name: str) -> str:
    return name.lower().replace(" ", "")

def collect_alinesellwia(root: Path) -> list[tuple[Path, int]]:
    samples = []
    dataset_path = root / "alinesellwia"
    if not dataset_path.exists():
        print(f"  [WARN] alinesellwia/ not found at {dataset_path}, skipping.")
        return samples

    for split in ["train", "test"]:
        split_path = dataset_path / split
        if not split_path.exists():
            print(f"  [WARN] alinesellwia/{split}/ not found, skipping.")
            continue
        for folder in sorted(split_path.iterdir()):
            if not folder.is_dir():
                continue
            normalized = normalize_folder_name(folder.name)
            label = ALINESELLWIA_FOLDER_MAP.get(normalized)
            if label is None:
                print(f"  [WARN] Alinesellwia: unknown folder '{folder.name}' "
                      f"(normalized: '{normalized}'), skipping.")
                continue
            for img in folder.rglob("*"):
                if is_image(img):
                    samples.append((img, label))

    print(f"  Alinesellwia: {len(samples):,} images")
    return samples


def stratified_split(
    samples: list[tuple[Path, int]]
) -> tuple[list, list, list]:
    """Split preserving class ratios across train/val/test."""
    by_class = defaultdict(list)
    for path, label in samples:
        by_class[label].append((path, label))

    train, val, test = [], [], []
    print("\n  Per-class split:")
    for label in sorted(by_class):
        items = by_class[label]
        random.shuffle(items)
        n       = len(items)
        n_train = int(n * TRAIN_RATIO)
        n_val   = int(n * VAL_RATIO)
        n_test  = n - n_train - n_val
        train  += items[:n_train]
        val    += items[n_train:n_train + n_val]
        test   += items[n_train + n_val:]
        print(f"    {CLASS_NAMES[label]:6s}:  "
              f"train={n_train:,}  val={n_val:,}  test={n_test:,}  total={n:,}")

    return train, val, test



def copy_split(
    samples: list[tuple[Path, int]],
    split_dir: Path,
    split_name: str
) -> dict[int, int]:
    counters: dict[int, int] = defaultdict(int)
    for src, label in samples:
        dest_dir = split_dir / CLASS_NAMES[label]
        dest_dir.mkdir(parents=True, exist_ok=True)
        counters[label] += 1
        dest = dest_dir / f"{src.stem}_{counters[label]}{src.suffix}"
        if dest.exists():
            dest = dest_dir / f"{src.stem}_{counters[label]}_b{src.suffix}"
        shutil.copy2(src, dest)
    return dict(counters)



def write_report(
    output_root: Path,
    source_counts: dict,
    split_stats: dict,
    total: int
):
    lines = [
        "=" * 62,
        "DATASET MERGE REPORT",
        "=" * 62,
        "",
        "Images per source:",
    ]
    for source, counts in source_counts.items():
        lines.append(f"  {source}:")
        for label in sorted(counts):
            lines.append(f"    {CLASS_NAMES[label]:12s}: {counts[label]:,}")

    lines += ["", "Split counts:"]
    for split_name, counters in split_stats.items():
        lines.append(f"  {split_name}:")
        for label in sorted(counters):
            lines.append(f"    {CLASS_NAMES[label]:12s}: {counters[label]:,}")

    fresh  = sum(split_stats[s].get(0, 0) for s in split_stats)
    stale  = sum(split_stats[s].get(1, 0) for s in split_stats)
    rotten = sum(split_stats[s].get(2, 0) for s in split_stats)

    lines += [
        "",
        "Overall class distribution:",
        f"  fresh : {fresh:,}  ({100*fresh/total:.1f}%)",
        f"  stale : {stale:,}  ({100*stale/total:.1f}%)",
        f"  rotten: {rotten:,}  ({100*rotten/total:.1f}%)",
        f"  TOTAL : {total:,}",
        "",
        "Label mapping:",
        "  Potdar       fresh_*           → 0 fresh",
        "               stale_*           → 1 stale",
        "  ULNN         Fresh/*           → 0 fresh",
        "               Rotten/*          → 2 rotten",
        "  Alinesellwia *_segar           → 0 fresh",
        "               *_segar_sedang    → 1 stale",
        "               *_busuk           → 2 rotten",
        "",
        "Notes:",
        "  - ULNN has NO stale class. Stale examples come only from",
        "    Potdar and Alinesellwia.",
        "  - Alinesellwia train/ and test/ were pooled then re-split.",
        "  - 'tomat _segar_sedang' space in folder name handled automatically.",
        "  - Use these class weights in your loss function to handle imbalance:",
        f"    w_fresh  = {(stale+rotten)/(2*fresh):.4f}",
        f"    w_stale  = {(fresh+rotten)/(2*stale):.4f}",
        f"    w_rotten = {(fresh+stale)/(2*rotten):.4f}",
        "=" * 62,
    ]

    report_path = output_root / "merge_report.txt"
    report_path.write_text("\n".join(lines))
    print(f"\n  Report saved to: {report_path}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    raw_root    = Path(RAW_DATA_ROOT)
    output_root = Path(OUTPUT_ROOT)
    output_root.mkdir(parents=True, exist_ok=True)

    print("Collecting images from each dataset...")
    potdar_samples       = collect_potdar(raw_root)
    ulnn_samples         = collect_ulnn(raw_root)
    alinesellwia_samples = collect_alinesellwia(raw_root)

    def count_by_label(samples):
        c: dict[int, int] = defaultdict(int)
        for _, l in samples:
            c[l] += 1
        return dict(c)

    source_counts = {
        "potdar":       count_by_label(potdar_samples),
        "ulnn":         count_by_label(ulnn_samples),
        "alinesellwia": count_by_label(alinesellwia_samples),
    }

    all_samples = potdar_samples + ulnn_samples + alinesellwia_samples
    print(f"\n  Grand total: {len(all_samples):,} images")

    print("\nSplitting (stratified)...")
    train, val, test = stratified_split(all_samples)

    print("\nCopying files...")
    split_stats = {}
    for split_name, samples in [("train", train), ("val", val), ("test", test)]:
        print(f"  Copying {split_name} ({len(samples):,} files)...")
        split_stats[split_name] = copy_split(
            samples, output_root / split_name, split_name
        )

    write_report(output_root, source_counts, split_stats, len(all_samples))

    print(f"\nDone! Merged dataset at: {output_root.resolve()}")
    print("\nFinal structure:")
    for split in ["train", "val", "test"]:
        for cls in ["fresh", "stale", "rotten"]:
            p = output_root / split / cls
            count = len(list(p.glob("*"))) if p.exists() else 0
            print(f"  {split:5s}/{cls:6s}/  {count:,} images")


if __name__ == "__main__":
    main()
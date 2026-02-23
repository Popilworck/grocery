from dataset import build_datasets

train_ds, val_ds = build_datasets("grocery/Vegetable Images/train", "grocery/Vegetable Images/validation")

# print("Number of classes:", len(train_ds.classes))
# print("Classes:", train_ds.classes)

# print("Train size:", len(train_ds))
# print("Val size:", len(val_ds))

# print("Class to index mapping:")
# print(train_ds.class_to_idx)

from torch.utils.data import DataLoader

train_loader = DataLoader(
    train_ds,
    batch_size=256,
    shuffle=True,
    num_workers=12,
    pin_memory=True,
    persistent_workers=True
)

val_loader = DataLoader(
    val_ds,
    batch_size=256,
    shuffle=False,
    num_workers=12,
    pin_memory=True,
    persistent_workers=True
)

images, labels = next(iter(train_loader))
print(images.shape)  # should be [B, 3, 224, 224]
print(labels.shape)  # should be [B]


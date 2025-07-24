import os
import json
import random
from tqdm import tqdm
from PIL import Image
import torch
from torchvision import transforms

captcha_length = 4
image_resize = (3, 64, 176)

download_dir = os.environ.get("DOWNLOAD_DIR")
if not download_dir:
    raise ValueError("Please set the environment variable DOWNLOAD_DIR.")
train_ratio = float(os.environ.get("TRAIN_RATIO", 0.8))
image_dir = os.path.join(download_dir, "right")
train_dir = os.path.join(download_dir, "train")
val_dir = os.path.join(download_dir, "val")
test_dir = os.path.join(download_dir, "test")

images = os.listdir(image_dir)
random.shuffle(images)
train_size = int(len(images) * train_ratio)
val_size = int(len(images) * (1 - train_ratio) / 2)
test_size = len(images) - train_size - val_size

os.makedirs(train_dir, exist_ok=True)
os.makedirs(val_dir, exist_ok=True)
os.makedirs(test_dir, exist_ok=True)

for img in images[:train_size]:
    os.rename(os.path.join(image_dir, img), os.path.join(train_dir, img))
for img in images[train_size:train_size + val_size]:
    os.rename(os.path.join(image_dir, img), os.path.join(val_dir, img))
for img in images[train_size + val_size:]:
    os.rename(os.path.join(image_dir, img), os.path.join(test_dir, img))

imgs = {
    train_dir: os.listdir(train_dir),
    val_dir: os.listdir(val_dir),
    test_dir: os.listdir(test_dir)
}
words = set()

transform = transforms.Compose([
    transforms.Resize(image_resize[1:]),
    transforms.ToTensor(),
])

pixel_sum, pixel_sq_sum = torch.zeros(image_resize[0]), torch.zeros(image_resize[0])
num_pixels, count = 0, 0

for folder, img_list in imgs.items():
    for img in tqdm(img_list, desc=f"Processing images in {folder}", ncols=100):
        word = list(img.split("_")[0])
        assert len(word) == captcha_length, f"label of image {img} does not have {captcha_length} characters."
        for c in word:
            words.add(c)
        image_path = os.path.join(folder, img)
        image = Image.open(image_path).convert('RGB')
        image = transform(image)

        assert image.shape[0] == image_resize[0], f"Image {img} does not have {image_resize[0]} channels."
        pixel_sum += image.sum(dim=(1, 2))
        pixel_sq_sum += (image ** 2).sum(dim=(1, 2))
        num_pixels += image.shape[1] * image.shape[2]
        count += 1

pixel_mean = pixel_sum / num_pixels
pixel_std = (pixel_sq_sum / num_pixels - pixel_mean ** 2).sqrt()
pixel_mean = [round(x.item(), 4) for x in pixel_mean]
pixel_std = [round(x.item(), 4) for x in pixel_std]
print(f"Mean: {pixel_mean}, Std: {pixel_std}")

words = sorted(list(words))
print(f"Total {count} images processed")
print(f"Total {train_size} training images, {val_size} validation images, {test_size} testing images.")
print(f"Total {len(words)} unique characters: [{', '.join(words)}]")

data = {
    "data_mean": pixel_mean,
    "data_std": pixel_std,
    "image_shape": image_resize,
    "characters": words,
    "tokenizer": {c: i for i, c in enumerate(words)},
    "captcha_length": captcha_length
}

with open(os.path.join(download_dir, "data.json"), "w") as f:
    json.dump(data, f, indent=4)

import torch
from torch.utils.data import Dataset
from torchvision import transforms
import json
import os
from PIL import Image

class NJUCaptchaDataset(Dataset):
    def __init__(self, image_paths: str, split: str = 'train', transform: transforms.Compose = None):
        with open(os.path.join(image_paths, 'data.json'), 'r') as f:
            data = json.load(f)
        self.image_paths = image_paths
        self.split = split
        self.images = os.listdir(os.path.join(image_paths, split))
        self.labels = [img.split('_')[0] for img in self.images]
        self.transform = transform if transform else transforms.Compose([
            transforms.Resize(data['image_shape'][-2:]),
            transforms.ToTensor(),
            transforms.Normalize(mean=data['data_mean'], std=data['data_std']),
        ])
        self.tokenizer = data['tokenizer']
        self.mapping = {v: k for k, v in self.tokenizer.items()}

    def __len__(self):
        return len(self.images)

    def __getitem__(self, idx):
        image_path = os.path.join(self.image_paths, self.split, self.images[idx])
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image {image_path} not found.")
        image = Image.open(image_path).convert('RGB')

        if self.transform:
            image = self.transform(image)

        label = self.labels[idx]
        return image, self.text2tensor(label)

    def text2tensor(self, text):
        return torch.tensor([self.tokenizer[char] for char in text])

    def tensor2text(self, tensor):
        return ''.join([self.mapping[int(idx)] for idx in tensor])

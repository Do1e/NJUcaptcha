import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
import json
import os
import time
import argparse
from tqdm import tqdm

from dataset import NJUCaptchaDataset
from model import CaptchaCNN


def calculate_accuracy(outputs, targets):
    predictions = torch.argmax(outputs, dim=-1)

    char_correct = (predictions == targets).float()
    char_accuracy = char_correct.mean().item()

    seq_correct = char_correct.all(dim=1).float()
    seq_accuracy = seq_correct.mean().item()

    return char_accuracy, seq_accuracy


def train_epoch(model, dataloader, criterion, optimizer, device, epoch):
    model.train()
    total_loss = 0
    num_batches = len(dataloader)

    for images, targets in tqdm(dataloader, desc=f'Epoch {epoch}', ncols=100):
        images, targets = images.to(device), targets.to(device)

        optimizer.zero_grad()
        outputs = model(images)

        loss = 0
        for i in range(outputs.shape[1]):
            loss += criterion(outputs[:, i, :], targets[:, i])
        loss /= outputs.shape[1]

        loss.backward()
        optimizer.step()

        total_loss += loss.item()

    avg_loss = total_loss / num_batches

    return avg_loss


def validate_epoch(model, dataloader, criterion, device):
    model.eval()
    total_loss = 0
    total_char_acc = 0
    total_seq_acc = 0
    num_batches = len(dataloader)

    with torch.no_grad():
        pbar = tqdm(dataloader, desc='Validation', ncols=100)
        for images, targets in pbar:
            images, targets = images.to(device), targets.to(device)

            outputs = model(images)

            loss = 0
            for i in range(outputs.shape[1]):
                loss += criterion(outputs[:, i, :], targets[:, i])
            loss /= outputs.shape[1]

            char_acc, seq_acc = calculate_accuracy(outputs, targets)

            total_loss += loss.item()
            total_char_acc += char_acc
            total_seq_acc += seq_acc

            pbar.set_postfix({
                'Loss': f'{loss.item():.4f}',
                'Char Acc': f'{char_acc:.4f}',
                'Seq Acc': f'{seq_acc:.4f}'
            })

    avg_loss = total_loss / num_batches
    avg_char_acc = total_char_acc / num_batches
    avg_seq_acc = total_seq_acc / num_batches

    return avg_loss, avg_char_acc, avg_seq_acc


def save_model(model, optimizer, epoch, loss, accuracy, filepath, input_shape=(3, 64, 176)):
    torch.save({
        'epoch': epoch,
        'model_state_dict': model.state_dict(),
        'optimizer_state_dict': optimizer.state_dict(),
        'loss': loss,
        'accuracy': accuracy,
    }, filepath)
    print(f"Model saved to {filepath}")
    if 'best' in filepath:
        input_shape = (1, *input_shape)
        device = next(model.parameters()).device
        path = os.path.dirname(filepath)
        torch.onnx.export(model, torch.randn(*input_shape, device=device), os.path.join(path, 'nju_captcha.onnx'),
                          input_names=['input'], output_names=['output'],
                          dynamic_axes={'input': {0: 'batch_size'}, 'output': {0: 'batch_size'}},
                          opset_version=11, do_constant_folding=True)


def load_model(model, optimizer, filepath):
    checkpoint = torch.load(filepath)
    model.load_state_dict(checkpoint['model_state_dict'])
    optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
    epoch = checkpoint['epoch']
    loss = checkpoint['loss']
    accuracy = checkpoint['accuracy']
    print(f"Model loaded from {filepath}, epoch: {epoch}, loss: {loss:.4f}, accuracy: {accuracy:.4f}")
    return epoch, loss, accuracy


def parse_args():
    parser = argparse.ArgumentParser(description='Train NJU Captcha CNN')
    parser.add_argument('--image_dir', type=str, help='Path to image directory', required=True)
    parser.add_argument('--batch_size', type=int, default=64, help='Batch size')
    parser.add_argument('--num_workers', type=int, default=8, help='Number of data loader workers')
    parser.add_argument('--epochs', type=int, default=100, help='Number of epochs')
    parser.add_argument('--lr', type=float, default=0.001, help='Learning rate')
    parser.add_argument('--device', type=str, default='auto', help='Device to use (auto/cpu/cuda)')
    parser.add_argument('--save_dir', type=str, default='checkpoints', help='Directory to save models')
    parser.add_argument('--resume', type=str, default=None, help='Path to checkpoint to resume from')
    parser.add_argument('--save_every', type=int, default=10, help='Save model every N epochs')
    return parser.parse_args()


def main():
    args = parse_args()

    if args.device == 'auto':
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    else:
        device = torch.device(args.device)
    print(f"Using device: {device}")

    os.makedirs(args.save_dir, exist_ok=True)

    with open(os.path.join(args.image_dir, 'data.json'), 'r') as f:
        data = json.load(f)

    num_classes = len(data['tokenizer'])
    captcha_length = data['captcha_length']
    print(f"Number of classes: {num_classes}")
    print(f"Captcha length: {captcha_length}")

    train_dataset = NJUCaptchaDataset(args.image_dir, split='train')
    val_dataset = NJUCaptchaDataset(args.image_dir, split='val')

    print(f"Train dataset size: {len(train_dataset)}")
    print(f"Validation dataset size: {len(val_dataset)}")

    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True, num_workers=args.num_workers)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False, num_workers=args.num_workers)

    model = CaptchaCNN(
        num_classes=num_classes,
        captcha_length=captcha_length,
        image_shape=data['image_shape'][-2:],
        channels=[16, 32, 48],
        conv_dropout=0.1,
        fc_dropout=0.3
    ).to(device)

    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"Total parameters: {total_params:,}")
    print(f"Trainable parameters: {trainable_params:,}")
    print(f"Model size: {total_params * 4 / (1024 ** 2):.2f} MB")

    optimizer = optim.Adam(model.parameters(), lr=args.lr, weight_decay=1e-4)
    criterion = nn.CrossEntropyLoss()
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=5)

    train_losses = []
    val_losses = []
    val_accs = []

    start_epoch = 0
    best_val_acc = 0
    best_epoch = 0

    if args.resume:
        start_epoch, val_loss, val_seq_acc = load_model(model, optimizer, args.resume)
        start_epoch += 1
        best_val_acc, best_epoch = val_seq_acc, start_epoch

    print(f"\nStarting training from epoch {start_epoch}...")
    print("=" * 80)

    start_time = time.time()


    for epoch in range(start_epoch, args.epochs):
        if optimizer.param_groups[0]['lr'] < 1e-7:
            print("Learning rate too low, stopping training.")
            break
        print(f"\nEpoch {epoch+1}/{args.epochs}")
        print("-" * 40)

        train_loss = train_epoch(
            model, train_loader, criterion, optimizer, device, epoch+1
        )

        val_loss, val_char_acc, val_seq_acc = validate_epoch(
            model, val_loader, criterion, device
        )

        scheduler.step(val_loss)

        train_losses.append(train_loss)
        val_losses.append(val_loss)
        val_accs.append(val_seq_acc)

        print(f"\nEpoch {epoch+1} Results:")
        print(f"Train - Loss: {train_loss:.4f}")
        print(f"Val   - Loss: {val_loss:.4f}, Char Acc: {val_char_acc:.4f}, Seq Acc: {val_seq_acc:.4f}")
        print(f"Current LR: {optimizer.param_groups[0]['lr']:.7f}")

        if val_seq_acc > best_val_acc:
            best_val_acc = val_seq_acc
            best_model_path = os.path.join(args.save_dir, 'best_model.pth')
            save_model(model, optimizer, epoch, val_loss, val_seq_acc, best_model_path, input_shape=data['image_shape'])
            print(f"New best validation accuracy: {best_val_acc:.4f}")
            best_epoch = epoch + 1

        if (epoch + 1) % args.save_every == 0:
            checkpoint_path = os.path.join(args.save_dir, f'checkpoint_epoch_{epoch+1}.pth')
            save_model(model, optimizer, epoch, val_loss, val_seq_acc, checkpoint_path, input_shape=data['image_shape'])

    final_model_path = os.path.join(args.save_dir, 'final_model.pth')
    save_model(model, optimizer, epoch, val_loss, val_seq_acc, final_model_path, input_shape=data['image_shape'])

    total_time = time.time() - start_time
    print(f"\nTraining completed in {total_time:.2f} seconds")
    print(f"Best validation accuracy: {best_val_acc:.4f}, achieved at epoch {best_epoch}")


if __name__ == '__main__':
    main()

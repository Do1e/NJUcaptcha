import argparse
import json
import os
import time
from tqdm import tqdm

import sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../build_dataset/NJUlogin'))
from captchaOCR import CaptchaOCR
from captchaOCR_ddddocr import CaptchaOCR as CaptchaOCR_ddddocr

def test(ocr, image_dir, test_images):
    correct = 0
    for image_name in tqdm(test_images):
        image_path = os.path.join(image_dir, 'test', image_name)
        label = image_name.split('_')[0]
        with open(image_path, 'rb') as f:
            text = ocr.get_text(f.read())
        if text == label:
            correct += 1
    return correct

def main():
    parser = argparse.ArgumentParser(description='Test NJU Captcha CNN')
    parser.add_argument('--image_dir', type=str, help='Path to image directory', required=True)
    args = parser.parse_args()

    image_dir = args.image_dir
    with open(os.path.join(image_dir, 'data.json'), 'r') as f:
        data = json.load(f)
    test_images = os.listdir(os.path.join(image_dir, 'test'))
    tokenizer = data['tokenizer']
    num_classes = len(tokenizer)
    captcha_length = data['captcha_length']

    print(f"length of test images: {len(test_images)}")
    print(f"number of classes: {num_classes}")
    print(f"length of captcha: {captcha_length}")

    print("Start testing model from ddddocr...")
    ocr = CaptchaOCR_ddddocr()
    start_time = time.time()
    correct = test(ocr, image_dir, test_images)
    end_time = time.time()
    print(f"{len(test_images) / (end_time - start_time):.2f} images/sec")
    print(f"Accuracy: {correct / len(test_images):.2%}")

    print("\nStart testing model by me...")
    ocr = CaptchaOCR()
    start_time = time.time()
    correct = test(ocr, image_dir, test_images)
    end_time = time.time()
    print(f"{len(test_images) / (end_time - start_time):.2f} images/sec")
    print(f"Accuracy: {correct / len(test_images):.2%}")


if __name__ == '__main__':
    main()

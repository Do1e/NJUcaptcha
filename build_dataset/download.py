
from NJUlogin import pwdLogin
import time
from tqdm import tqdm
import os
import random


username = os.environ.get("NJU_USERNAME")
password = os.environ.get("NJU_PASSWORD")
download_dir = os.environ.get("DOWNLOAD_DIR")
num_require = os.environ.get("NUM_REQUIRE", 100000)

if not username or not password or not download_dir:
    raise ValueError("Please set the environment variables NJU_USERNAME, NJU_PASSWORD and NJU_DOWNLOAD_DIR.")

right_dir = os.path.join(download_dir, "right")
wrong_dir = os.path.join(download_dir, "wrong")

if not os.path.exists(right_dir):
    os.makedirs(right_dir)
if not os.path.exists(wrong_dir):
    os.makedirs(wrong_dir)

num_existed = len(os.listdir(right_dir)) + len(os.listdir(wrong_dir))
if num_existed >= num_require:
    print(f"Already have {num_existed} pictures, no need to download more.")
    exit(0)
pbar = tqdm(total=num_require - num_existed, desc="Downloading Captchas", unit="captcha", ncols=100)
wrong, count = 0, 0
while len(os.listdir(right_dir)) + len(os.listdir(wrong_dir)) < num_require:
    session = pwdLogin(username, password)
    ret = session.login(right_dir, wrong_dir)
    if not ret:
        wrong += 1
    count += 1
    pbar.set_description(f"Downloading Captchas (attempt {count}, wrong {wrong})")
    session.logout()
    time.sleep(random.randint(2, 3))
    pbar.update(1)

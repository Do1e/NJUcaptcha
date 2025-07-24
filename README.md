# 南大统一身份认证验证码（数据集、识别模型、识别服务）

![效果](img/效果.gif)

## 数据集下载

链接： [https://pan.do1e.cn/%E5%8D%97%E4%BA%AC%E5%A4%A7%E5%AD%A6/NJU-captcha-dataset.7z](https://pan.do1e.cn/%E5%8D%97%E4%BA%AC%E5%A4%A7%E5%AD%A6/NJU-captcha-dataset.7z)，解压密码：`@Do1e`

包含了 100,000 张验证码图片，文件名称为`{验证码文本}_{图片md5}.jpg`。验证码文本标注为全小写。

基于 [ddddocr](https://github.com/sml2h3/ddddocr) 和 [NJUlogin](https://github.com/Do1e/NJUlogin) 进行识别与正确性验证，识别错误的为手动标注。

## 数据集构建

[build_dataset](build_dataset) 目录下包含了南大统一身份认证验证码的数据集构建代码。

需要先配置下述环境变量：  
1. `NJU_USERNAME`：南大统一身份认证用户名
2. `NJU_PASSWORD`：南大统一身份认证密码
3. `DOWNLOAD_DIR`：验证码图片下载目录
4. `NUM_REQUIRE`：需要下载的验证码图片数量，默认为 100,000

之后运行脚本 [build_dataset/download.py](build_dataset/download.py)，会将验证码图片下载到指定目录，其中正确的验证码放在 `right` 文件夹中，错误的验证码放在 `wrong` 文件夹中，需要手动重命名并移动到 `right` 文件夹中。

完成后还需运行脚本 [build_dataset/post_processing.py](build_dataset/post_processing.py)，分配训练、验证和测试集并生成数据集信息，需要指定环境变量 `DOWNLOAD_DIR` 和 `TRAIN_RATIO`（训练集比例，默认为 0.8）。

## 识别模型

[model](model) 目录下包含了南大统一身份认证验证码的识别模型及其训练代码。

设计了一个 [轻量化的CNN模型](model/model.py)  
参数量 588,424  
模型尺寸 2.24MiB

训练脚本： [model/train.py](model/train.py)  
或者直接使用导出的 [onnx](model/checkpoints/nju_captcha.onnx)。

查看模型架构可以使用 [netron](https://netron.app/) 打开 [onnx](model/checkpoints/nju_captcha.onnx)。

## 识别服务
[service](service) 目录下包含了南大统一身份认证验证码的识别服务代码。

也可以使用我在 [vercel](https://njucaptcha.vercel.app) 上部署的服务。

#### docker

```bash
docker build -t nju-captcha-service .
docker run -d --name nju-captcha-service -p 8000:8000 nju-captcha-service
```

nginx 配置示例：

```nginx
server {
    listen 80;
    listen [::]:80;
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name example.com;
    if ($scheme = http) {
        return 301 https://$host$request_uri;
    }
    location / {
        proxy_pass http://127.0.0.1:8000$request_uri;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Real-PORT $remote_port;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

#### vercel

```bash
npm install -g vercel
vercel login
vercel --prod
```

#### 测试

```bash
captcha_b64=$(base64 -i captcha.jpg | tr -d '\n')
curl -X POST 'https://njucaptcha.vercel.app' \
     -H 'Content-Type: application/x-www-form-urlencoded' \
     -d "captcha=$(echo "$captcha_b64" | jq -s -R -r @uri)"
```

#### 油猴脚本自动填充

```javascript
// ==UserScript==
// @name         南大统一身份认证自动填充验证码
// @namespace    https://bubbleioa.top/
// @version      1.0
// @description  南大统一身份认证自动填充验证码
// @author       Bubbleioa, Do1e
// @license      GPL-3.0
// @match        https://authserver.nju.edu.cn/authserver/login*
// @icon         https://www.do1e.cn/favicon.ico
// @grant        none
// @run-at       document-body
// ==/UserScript==

function sleep(time) {
    return new Promise((resolve) => setTimeout(resolve, time));
}


(function () {
    'use strict';
    const serverUrl = 'https://njucaptcha.vercel.app'; // 替换为你的验证码识别服务地址
    // 等待图片加载完成
    sleep(500).then(() => {
        // 获取验证码 base64 编码
        var canvas = document.createElement('canvas');
        var context = canvas.getContext('2d');
        var inputField = document.getElementById('captchaResponse');
        var img = document.getElementById('captchaImg');
        canvas.height = img.naturalHeight;
        canvas.width = img.naturalWidth;
        context.drawImage(img, 0, 0, img.naturalWidth, img.naturalHeight);
        var base64String = canvas.toDataURL();
        // 发送到验证码识别服务器 修改输入框
        fetch(serverUrl, {
            method: 'POST',
            mode: 'cors',
            cache: 'no-cache',
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            redirect: 'follow',
            referrerPolicy: 'no-referrer',
            body: new URLSearchParams({
                'captcha': base64String.split(',')[1]
            })
        }).then((resp) => resp.text()).then(text => {
            inputField.value = text;
        });
    });
})();
```

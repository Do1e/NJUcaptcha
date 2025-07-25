// ==UserScript==
// @name         NJU Captcha Auto-Fill ONNX
// @downloadURL  https://raw.githubusercontent.com/Do1e/NJUcaptcha/refs/heads/main/njucaptcha_onnx.user.js
// @updateURL    https://raw.githubusercontent.com/Do1e/NJUcaptcha/refs/heads/main/njucaptcha_onnx.user.js
// @version      1.0
// @description  使用 ONNX Runtime Web 在客户端自动识别南大统一身份认证验证码
// @author       Bubbleioa, Do1e
// @license      GPL-3.0
// @match        https://authserver.nju.edu.cn/authserver/login*
// @icon         https://www.do1e.cn/favicon.ico
// @grant        GM_xmlhttpRequest
// @connect      *
// @require      https://cdn.jsdelivr.net/npm/onnxruntime-web/dist/ort.min.js
// @resource     ONNX_MODEL https://cdn.jsdelivr.net/gh/Do1e/NJUcaptcha@main/model/checkpoints/nju_captcha.onnx
// @grant        GM_getResourceURL
// @run-at       document-body
// ==/UserScript==

function waitForElement(selector, callback) {
    const element = document.querySelector(selector);
    if (element) {
        callback(element);
    } else {
        const observer = new MutationObserver(() => {
            const element = document.querySelector(selector);
            if (element) {
                observer.disconnect();
                callback(element);
            }
        });
        observer.observe(document.body, { childList: true, subtree: true });
    }
}

(async function () {
    'use strict';

    const modelURL = await GM_getResourceURL('ONNX_MODEL');
    const wasmBaseURL = 'https://cdn.jsdelivr.net/npm/onnxruntime-web/dist/';
    ort.env.wasm.wasmPaths = wasmBaseURL;

    const charset = ['1', '2', '3', '4', '5', '6', '7', '8', 'a', 'b', 'c', 'd', 'e', 'f', 'h', 'k', 'n', 'p', 'q', 'x', 'y', 'z'];
    const resizeWidth = 176;
    const resizeHeight = 64;
    const charCount = 4;
    const numClasses = 22;
    const mean = [0.743, 0.7432, 0.7431];
    const std = [0.1917, 0.1918, 0.1917];

    const modelPromise = new Promise((resolve, reject) => {
        GM_xmlhttpRequest({
            method: "GET",
            url: modelURL,
            responseType: "arraybuffer",
            onload: async function(response) {
                if (response.status !== 200) {
                    reject(new Error(`下载ONNX模型失败，状态码: ${response.status}`));
                    return;
                }
                try {
                    const modelData = response.response;
                    const session = await ort.InferenceSession.create(modelData, {
                        executionProviders: ['wasm']
                    });
                    resolve(session);
                } catch (error) {
                    reject(error);
                }
            },
            onerror: function(error) {
                reject(new Error('下载ONNX模型失败: ' + error));
            }
        });
    });

    waitForElement('#captchaImg', async function(img) {
        try {
            const canvas = document.createElement('canvas');
            canvas.width = resizeWidth;
            canvas.height = resizeHeight;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(img, 0, 0, resizeWidth, resizeHeight);
            const imageData = ctx.getImageData(0, 0, resizeWidth, resizeHeight);
            const { data } = imageData;


            const float32Data = new Float32Array(3 * resizeHeight * resizeWidth);
            for (let i = 0; i < resizeHeight * resizeWidth; i++) {
                const r = data[i * 4] / 255.0;
                const g = data[i * 4 + 1] / 255.0;
                const b = data[i * 4 + 2] / 255.0;

                float32Data[i] = (r - mean[0]) / std[0];
                float32Data[i + resizeHeight * resizeWidth] = (g - mean[1]) / std[1];
                float32Data[i + 2 * resizeHeight * resizeWidth] = (b - mean[2]) / std[2];
            }

            const session = await modelPromise;

            const inputTensor = new ort.Tensor('float32', float32Data, [1, 3, resizeHeight, resizeWidth]);
            const feeds = { 'input': inputTensor };

            const results = await session.run(feeds);
            const outputTensor = results.output;

            const outputData = outputTensor.data;
            let text = '';

            for (let i = 0; i < charCount; i++) {
                const startIndex = i * numClasses;
                const endIndex = startIndex + numClasses;
                const classScores = Array.from(outputData.slice(startIndex, endIndex));

                let maxScore = -Infinity;
                let maxIndex = -1;
                for(let j = 0; j < classScores.length; j++) {
                    if (classScores[j] > maxScore) {
                        maxScore = classScores[j];
                        maxIndex = j;
                    }
                }
                text += charset[maxIndex];
            }

            waitForElement('#captchaResponse', function(inputField) {
                inputField.value = text;
            });

        } catch (error) {
            console.error('验证码识别出错:', error);
        }
    });
})();

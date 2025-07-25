// ==UserScript==
// @name         NJU Captcha Auto-Fill
// @downloadURL  https://raw.githubusercontent.com/Do1e/NJUcaptcha/refs/heads/main/njucaptcha.user.js
// @updateURL    https://raw.githubusercontent.com/Do1e/NJUcaptcha/refs/heads/main/njucaptcha.user.js
// @version      1.0
// @description  南大统一身份认证自动填充验证码
// @author       Bubbleioa, Do1e
// @license      GPL-3.0
// @match        https://authserver.nju.edu.cn/authserver/login*
// @icon         http://www.do1e.cn/favicon.ico
// @grant        none
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

(function () {
    'use strict';
    const serverUrl = 'https://njucaptcha.vercel.app';

    let captchaText = '';

    waitForElement('#captchaImg', (img) => {
        const processCaptcha = () => {
            // 获取验证码 base64 编码
            var canvas = document.createElement('canvas');
            var context = canvas.getContext('2d');
            canvas.height = img.naturalHeight;
            canvas.width = img.naturalWidth;
            context.drawImage(img, 0, 0, img.naturalWidth, img.naturalHeight);
            var base64String = canvas.toDataURL();

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
                captchaText = text;
                waitForElement('#captchaResponse', (inputField) => {
                    inputField.value = captchaText;
                });
            });
        };

        if (img.complete && img.naturalHeight !== 0) {
            processCaptcha();
        } else {
            img.onload = processCaptcha;
        }
    });
})();

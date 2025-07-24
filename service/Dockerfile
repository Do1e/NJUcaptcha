FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip3 install -i https://mirror.nju.edu.cn/pypi/web/simple --no-cache-dir -r requirements.txt
COPY captchaOCR ./captchaOCR
COPY main.py .
CMD ["python3", "main.py"]

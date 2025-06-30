FROM python:3.9-slim

WORKDIR /app

# 安装系统依赖（用于textract和各种文档格式处理）
RUN apt-get update && apt-get install -y \
    antiword \
    poppler-utils \
    tesseract-ocr \
    libreoffice \
    libxml2-dev \
    libxslt1-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 配置pip使用国内镜像源并增加超时时间
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple \
    && pip config set global.timeout 1000 \
    && pip config set global.retries 10

# 更新pip到最新版本
RUN pip install --no-cache-dir --upgrade pip

# 复制依赖文件并安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用程序文件
COPY *.py .

EXPOSE 9020

# 启动API服务
CMD ["python", "main.py"]
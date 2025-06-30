# Waxberry 插件

一个用于文本、图像和语音处理的综合插件，为各种AI驱动功能提供统一的API。

## 功能特性

- **文本处理**
  - 从各种来源提取文本
  - 文本分析和处理
  - 自然语言理解

- **图像处理**
  - 图像转文本转换（OCR）
  - 从文本生成图像
  - 图像分析和分类

- **语音处理**
  - 语音转文本转换
  - 通过WebSocket进行实时语音处理
  - 语音文件处理

## 安装

1. 克隆仓库：
```bash
git clone https://github.com/Jiangxue-Waxberry/waxberry-plugin.git
cd waxberry-plugin
```

2. 创建并激活虚拟环境：
```bash
conda create --name waxberry-plugin python=3.9.21
conda activate waxberry-plugin
```

3. 安装依赖：
```bash
pip install --no-cache-dir -r requirements.txt
```

## 配置

1. 在项目根目录创建 `.env` 文件：
```env
OPENAI_API_KEY=your_openai_api_key
BYTEDANCE_API_KEY=your_bytedance_api_key
```

2. 如需要，在 `src/config/settings.py` 中更新配置。

## 使用方法

### 启动服务器

```bash
python main.py
```

服务器默认将在 `http://localhost:9020` 启动。

### API 端点

#### 接口文档：
http://0.0.0.0:9020/api/docs

#### 文本处理
- `POST /api/v1/extract` - 从各种来源提取文本
- `POST /api/v1/process` - 使用AI处理文本

#### 图像处理
- `POST /api/v1/imageToText` - 将图像转换为文本
- `POST /api/v1/generateImage` - 从文本生成图像

#### 语音处理
- `POST /api/v1/voiceToText` - 将语音转换为文本
- `POST /api/v1/processVoiceFile` - 处理语音文件
- `WS /ws/voice` - 实时语音处理的WebSocket端点

### 使用示例

```python
import requests

# 文本提取
response = requests.post('http://localhost:9020/api/v1/extract', 
    json={'text': '要处理的示例文本'})
print(response.json())

# 图像处理
with open('image.jpg', 'rb') as f:
    response = requests.post('http://localhost:9020/api/v1/imageToText',
        files={'image': f})
print(response.json())
```

## 开发

### 项目结构
```
waxberry-plugin/
├── src/
│   ├── api/          # API路由和服务
│   ├── core/         # 核心处理模块
│   ├── utils/        # 工具函数
│   └── config/       # 配置
├── tests/            # 测试文件
└── main.py          # 应用程序入口点
```

### 运行测试
```bash
python -m unittest discover tests
```

## 贡献

1. Fork 仓库
2. 创建功能分支
3. 提交您的更改
4. 推送到分支
5. 创建 Pull Request

## 许可证
Apache License - 查看 [LICENSE](LICENSE) 文件了解详情

## 联系方式
- 邮箱: [info@yangmeigongye.com]

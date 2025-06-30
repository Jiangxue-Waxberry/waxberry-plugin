# Waxberry Plugin

A comprehensive plugin for text, image, and voice processing, providing a unified API for various AI-powered functionalities.

## Features

- **Text Processing**
  - Text extraction from various sources
  - Text analysis and processing
  - Natural language understanding

- **Image Processing**
  - Image to text conversion (OCR)
  - Image generation from text
  - Image analysis and classification

- **Voice Processing**
  - Voice to text conversion
  - Real-time voice processing via WebSocket
  - Voice file processing

## Installation

1. Clone the repository:
```bash
git clone https://github.com/Jiangxue-Waxberry/waxberry-plugin.git
cd waxberry-plugin
```

2. Create and activate a virtual environment:
```bash
conda create --name waxberry-plugin python=3.9.21
conda activate waxberry-plugin
```

3. Install dependencies:
```bash
pip install --no-cache-dir -r requirements.txt
```

## Configuration

1. Create a `.env` file in the project root:
```env
OPENAI_API_KEY=your_openai_api_key
BYTEDANCE_API_KEY=your_bytedance_api_key
```

2. Update configuration in `src/config/settings.py` if needed.

## Usage

### Starting the Server

```bash
python main.py
```

The server will start on `http://localhost:9020` by default.

### API Endpoints

#### 接口文档：
http://0.0.0.0:9020/api/docs

#### Text Processing
- `POST /api/v1/extract` - Extract text from various sources
- `POST /api/v1/process` - Process text with AI

#### Image Processing
- `POST /api/v1/imageToText` - Convert image to text
- `POST /api/v1/generateImage` - Generate image from text

#### Voice Processing
- `POST /api/v1/voiceToText` - Convert voice to text
- `POST /api/v1/processVoiceFile` - Process voice file
- `WS /ws/voice` - WebSocket endpoint for real-time voice processing

### Example Usage

```python
import requests

# Text extraction
response = requests.post('http://localhost:9020/api/v1/extract', 
    json={'text': 'Sample text to process'})
print(response.json())

# Image processing
with open('image.jpg', 'rb') as f:
    response = requests.post('http://localhost:9020/api/v1/imageToText',
        files={'image': f})
print(response.json())
```

## Development

### Project Structure
```
waxberry-plugin/
├── src/
│   ├── api/          # API routes and services
│   ├── core/         # Core processing modules
│   ├── utils/        # Utility functions
│   └── config/       # Configuration
├── tests/            # Test files
└── main.py          # Application entry point
```

### Running Tests
```bash
python -m unittest discover tests
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License
Apache License - see the [LICENSE](LICENSE) file for details

## Contact
- Email: [info@yangmeigongye.com] 

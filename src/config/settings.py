from pathlib import Path
from dotenv import load_dotenv
from dataclasses import dataclass, field
from typing import List
from .config import (
    BASE_URL,
    API_KEY,
    MODEL_NAME,
    IMAGE_MODEL_NAME,
    API_HOST,
    API_PORT,
    DEBUG_MODE,
    UPLOAD_FOLDER,
    MAX_CONTENT_LENGTH,
    DOUBAO_APP_ID,
    DOUBAO_TOKEN,
    DOUBAO_BASE_URL,
    DOUBAO_STREAM_BASE_URL,
    DOUBAO_AK,
    DOUBAO_SK
)

# 加载环境变量
load_dotenv()

# # 项目根目录
# BASE_DIR = Path(__file__).resolve().parent.parent.parent
#
# # 支持的图片格式
# supported_image_formats = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']

@dataclass
class Settings:
    """应用配置类"""
    # 项目根目录
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    
    # 支持的图片格式
    supported_image_formats: List[str] = field(default_factory=lambda: ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'])
    
    # API配置
    base_url: str = BASE_URL
    api_key: str = API_KEY
    model_name: str = MODEL_NAME
    image_model_name: str = IMAGE_MODEL_NAME

    # 豆包语音识别配置
    doubao_app_id: str = DOUBAO_APP_ID
    doubao_token: str = DOUBAO_TOKEN
    doubao_base_url: str = DOUBAO_BASE_URL
    doubao_stream_base_url: str = DOUBAO_STREAM_BASE_URL

    doubao_ak: str = DOUBAO_AK
    doubao_sk: str = DOUBAO_SK

    # 服务器配置
    api_host: str = API_HOST
    api_port: int = API_PORT
    debug_mode: bool = DEBUG_MODE
    
    # 文件上传配置
    upload_folder: str = UPLOAD_FOLDER
    max_content_length: int = MAX_CONTENT_LENGTH
    
    def __post_init__(self):
        """初始化后的验证"""
        self._validate_config()
    
    def _validate_config(self):
        """验证配置"""
        if not self.api_key:
            raise ValueError("API密钥不能为空")
        
        if not self.base_url.startswith(('http://', 'https://')):
            raise ValueError("BASE_URL必须是有效的URL")
        
        if self.api_port < 1 or self.api_port > 65535:
            raise ValueError("API端口必须在1-65535之间")
    
    @property
    def is_debug(self) -> bool:
        """是否处于调试模式"""
        return self.debug_mode
    
    def get_api_url(self, endpoint: str) -> str:
        """获取完整的API URL"""
        return f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    
    def get_upload_path(self, filename: str) -> str:
        """获取文件上传路径"""
        return f"{self.upload_folder}/{filename}"

# 创建全局配置实例
settings = Settings()

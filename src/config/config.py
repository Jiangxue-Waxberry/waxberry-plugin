"""
配置文件
从外部配置文件加载配置，如果加载失败则使用默认值
"""
import os
from .external_loader import load_external_config

# 尝试加载外部配置
try:
    external_config = load_external_config()
    
    # 从外部配置中导入所有变量
    globals().update(external_config)
    
    print("✓ 使用外部配置文件")
    
except Exception as e:
    print(f"⚠️ 无法加载外部配置，使用默认值: {e}")

    # 默认配置值
    BASE_URL = ''
    API_KEY = ''
    MODEL_NAME = ''
    IMAGE_MODEL_NAME = ''

    # 豆包语音识别配置
    DOUBAO_APP_ID = ''
    DOUBAO_TOKEN = ''
    DOUBAO_BASE_URL = ''
    DOUBAO_STREAM_BASE_URL = ''

    DOUBAO_AK = ''
    DOUBAO_SK = ''

    # 服务器配置
    API_HOST = ''
    API_PORT = 8080
    DEBUG_MODE = False

    # 文件上传配置
    FILESERVER_UPLOAD_URL = ''
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    print("⚠️ 请确保外部配置文件存在且包含正确的配置项")
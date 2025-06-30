"""
Flask应用初始化
"""

import logging
from flask import Flask
from flask_socketio import SocketIO
from flask_restx import Api
from src.api.routes.image_routes import image_bp, ns as image_ns
from src.api.routes.voice_routes import voice_bp, ns as voice_ns
from src.api.routes.text_routes import text_bp, ns as text_ns
from src.api.routes.health_routes import health_bp, ns as health_ns

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("voice_recognition_api")

def create_app() -> Flask:
    """创建Flask应用"""
    app = Flask(__name__)
    
    # 初始化API文档
    api = Api(
        app,
        version='1.0',
        title='Waxberry-Plugin API',
        description='Waxberry-Plugin API 文档',
        doc='/api/docs',
        prefix='/api'
    )
    
    # 添加所有命名空间
    api.add_namespace(health_ns)
    api.add_namespace(image_ns)
    api.add_namespace(voice_ns)
    api.add_namespace(text_ns)
    
    # 初始化SocketIO
    socketio = SocketIO(
        app,
        cors_allowed_origins="*",
        async_mode='eventlet',
        logger=False,  # 禁用 Socket.IO 日志
        engineio_logger=False,  # 禁用 Engine.IO 日志
        path='/socket.io',
        ping_timeout=60,
        ping_interval=25,
        max_http_buffer_size=1e8,
        always_connect=True,  # 保持连接
        allow_upgrades=True  # 允许升级到WebSocket
    )
    
    # 注册蓝图
    app.register_blueprint(image_bp)
    app.register_blueprint(voice_bp)
    app.register_blueprint(text_bp)
    app.register_blueprint(health_bp)
    
    # 将socketio实例添加到app对象
    app.socketio = socketio
    
    return app 
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
API服务器
提供图像处理、语音识别等服务接口
"""

import logging
import platform
import sys
import os
from datetime import datetime
from src.api.app import create_app
from src.config.settings import settings
from src.api.routes.stream_voice_routes import VoiceRecognitionService

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def print_startup_info():
    """打印启动信息"""
    # 在调试模式下，只在主进程中打印启动信息
    if settings.debug_mode and os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        return
        
    logger.info("=" * 50)
    logger.info("Waxberry-Plugin API服务器启动")
    logger.info("=" * 50)
    logger.info(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Python版本: {platform.python_version()}")
    logger.info(f"操作系统: {platform.platform()}")
    logger.info(f"服务器地址: http://{settings.api_host}:{settings.api_port}")
    logger.info(f"API文档地址: http://{settings.api_host}:{settings.api_port}/api/docs")
    logger.info(f"调试模式: {'开启' if settings.debug_mode else '关闭'}")
    logger.info("=" * 50)

def main():
    """主函数"""
    try:
        # 打印启动信息
        print_startup_info()
        
        # 创建应用
        app = create_app()
        socketio = app.socketio
        
        # 创建语音识别服务
        service = VoiceRecognitionService(app, socketio)
        
        # 启动ASR工作线程
        service.start_asr_worker()
        
        # 运行服务器
        try:
            socketio.run(
                app,
                host=settings.api_host,
                port=settings.api_port,
                debug=settings.debug_mode,
                use_reloader=False
            )
        except Exception as e:
            logger.error(f"服务器运行出错: {str(e)}", exc_info=True)
        finally:
            # 停止ASR工作线程
            service.stop_asr_worker()
            # 关闭全局事件循环
            service.loop.close()
        
    except Exception as e:
        logger.error(f"服务器启动失败: {str(e)}")
        raise

if __name__ == '__main__':
    main()
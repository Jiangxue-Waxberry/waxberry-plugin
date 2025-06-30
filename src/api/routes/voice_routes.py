"""
语音处理路由模块

本模块提供语音处理相关的API接口，主要功能包括：
1. 语音转文本 (voiceToText)：将语音文件转换为文本内容
2. 支持多种音频格式：mp3, wav, pcm, ogg
3. 支持两种上传方式：表单文件上传和二进制流上传
4. 提供详细的处理结果，包括文本内容、音频时长、段落信息等

API 接口说明：
1. /api/v1/voiceToText (POST)
   - 功能：将语音文件转换为文本
   - 支持格式：mp3, wav, pcm, ogg
   - 上传方式：
     * multipart/form-data：通过表单上传文件
     * application/octet-stream：直接上传二进制数据
   - 响应格式：
     * 成功：返回识别的文本内容和元数据
     * 失败：返回错误信息

使用示例：
1. 表单文件上传：
   curl -X POST "http://localhost:9020/api/v1/voiceToText" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@audio.wav"

2. 二进制流上传：
   curl -X POST "http://localhost:9020/api/v1/voiceToText" \
     -H "Content-Type: application/octet-stream" \
     --data-binary "@audio.wav"
"""

from flask import Blueprint, request, jsonify
from flask_restx import Resource, Namespace
from src.api.services.voice_service import VoiceService
from src.utils.logging import get_logger
import time

# 创建蓝图
voice_bp = Blueprint('voice', __name__)

# 创建命名空间
ns = Namespace('voice', description='语音处理接口')

# 创建日志记录器
logger = get_logger(__name__)

# 创建语音服务实例
voice_service = VoiceService()

@ns.route('/api/v1/voiceToText')
class VoiceToText(Resource):
    @ns.doc('voice_to_text',
        responses={
            200: '成功',
            400: '请求参数错误',
            500: '服务器错误'
        }
    )
    def post(self):
        """
        语音转文本接口
        
        功能：
        1. 接收语音文件并转换为文本
        2. 支持多种语音格式（mp3, wav, pcm, ogg）
        
        支持两种上传方式：
        1. 表单文件上传 (multipart/form-data)
           - 通过 'file' 字段上传语音文件
           - 文件格式从文件名扩展名自动识别
        2. 二进制流直接上传 (application/octet-stream)
           - 直接发送语音文件二进制数据
           - 通过查询参数 format 指定文件格式（默认 mp3）
        
        请求参数：
        1. 表单上传：
           - file: 语音文件（必填）
        2. 二进制流上传：
           - format: 文件格式（可选，默认 mp3）
        
        响应格式：
        {
            "success": true/false,          # 是否成功
            "text": "识别的文本内容",        # 成功时返回
            "file_type": "文件格式",         # 处理的文件格式
            "metadata": {                   # 元数据信息
                "duration_seconds": 10.5,    # 音频时长（秒）
                "paragraphs_count": 2,       # 段落数量
                "paragraphs_info": [         # 段落详细信息
                    {
                        "text": "段落文本",   # 段落内容
                        "start_time": 0.0,    # 开始时间（秒）
                        "end_time": 5.2,      # 结束时间（秒）
                        "word_count": 10      # 词数
                    }
                ],
                "word_count_total": 25,      # 总词数
                "process_time_seconds": 2.5   # 处理时间（秒）
            },
            "error": "错误信息"              # 失败时返回
        }
        
        错误码：
        400: 请求参数错误（如未提供文件、不支持的文件格式等）
        500: 服务器内部错误
        
        示例：
        1. 表单上传：
           curl -X POST "http://localhost:9020/api/v1/voiceToText" \
             -H "Content-Type: multipart/form-data" \
             -F "file=@audio.wav"
        
        2. 二进制流上传：
           curl -X POST "http://localhost:9020/api/v1/voiceToText" \
             -H "Content-Type: application/octet-stream" \
             --data-binary "@audio.wav"
        """
        try:
            audio_bytes = None
            file_format = "mp3"  # 默认格式

            # 检查请求类型
            if request.content_type and request.content_type.startswith('application/octet-stream'):
                # 处理二进制流上传
                logger.info("检测到二进制流上传")
                audio_bytes = request.get_data()
                # 从查询参数获取文件格式，如果没有则使用默认值
                file_format = request.args.get('format', 'mp3').lower()
                logger.info(f"从查询参数获取文件格式: {file_format}")
            elif 'file' in request.files:
                # 处理表单文件上传
                logger.info("检测到表单文件上传")
                file = request.files['file']
                if file.filename == '':
                    return jsonify({
                        "success": False,
                        "error": "未选择文件"
                    }), 400

                # 获取文件格式（扩展名）
                file_format = file.filename.split('.')[-1].lower()
                logger.info(f"从文件名获取文件格式: {file_format}")

                # 读取文件内容
                audio_bytes = file.read()
            else:
                return jsonify({
                    "success": False,
                    "error": "未提供音频数据，请使用表单文件上传或二进制流上传"
                }), 400

            # 验证文件格式
            if file_format not in ['mp3', 'wav', 'pcm', 'ogg']:  # 支持的格式
                return jsonify({
                    "success": False,
                    "error": f"不支持的文件格式: {file_format}"
                }), 400

            # 验证音频数据
            if not audio_bytes or len(audio_bytes) == 0:
                return jsonify({
                    "success": False,
                    "error": "音频数据为空"
                }), 400

            # 记录开始处理时间，用于计算总处理时间
            start_time = time.time()
            logger.info(f"开始处理音频文件，大小: {len(audio_bytes) / 1024:.2f}KB，格式: {file_format}")

            # 调用语音服务处理音频
            result = voice_service.voice_to_text(audio_bytes, file_format)
            
            # 计算处理时间
            process_time = time.time() - start_time
            logger.info(f"音频处理完成，耗时: {process_time:.2f}秒")
            
            # 添加处理时间到结果中
            if result.get("success", False) and "metadata" in result:
                result["metadata"]["process_time_seconds"] = process_time
                
            return jsonify(result)

        except Exception as e:
            logger.error(f"语音转文本失败: {str(e)}", exc_info=True)
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

@voice_bp.route('/api/v1/voiceToText', methods=['POST'])
def voice_to_text():
    """
    语音转文本接口
    
    功能：
    1. 接收语音文件并转换为文本
    2. 支持多种语音格式（mp3, wav, pcm, ogg）
    
    支持两种上传方式：
    1. 表单文件上传 (multipart/form-data)
       - 通过 'file' 字段上传语音文件
       - 文件格式从文件名扩展名自动识别
    2. 二进制流直接上传 (application/octet-stream)
       - 直接发送语音文件二进制数据
       - 通过查询参数 format 指定文件格式（默认 mp3）
    
    请求参数：
    1. 表单上传：
       - file: 语音文件（必填）
    2. 二进制流上传：
       - format: 文件格式（可选，默认 mp3）
    
    响应格式：
    {
        "success": true/false,          # 是否成功
        "text": "识别的文本内容",        # 成功时返回
        "file_type": "文件格式",         # 处理的文件格式
        "metadata": {                   # 元数据信息
            "duration_seconds": 10.5,    # 音频时长（秒）
            "paragraphs_count": 2,       # 段落数量
            "paragraphs_info": [         # 段落详细信息
                {
                    "text": "段落文本",   # 段落内容
                    "start_time": 0.0,    # 开始时间（秒）
                    "end_time": 5.2,      # 结束时间（秒）
                    "word_count": 10      # 词数
                }
            ],
            "word_count_total": 25,      # 总词数
            "process_time_seconds": 2.5   # 处理时间（秒）
        },
        "error": "错误信息"              # 失败时返回
    }
    
    错误码：
    400: 请求参数错误（如未提供文件、不支持的文件格式等）
    500: 服务器内部错误
    
    示例：
    1. 表单上传：
       curl -X POST "http://localhost:9020/api/v1/voiceToText" \
         -H "Content-Type: multipart/form-data" \
         -F "file=@audio.wav"
    
    2. 二进制流上传：
       curl -X POST "http://localhost:9020/api/v1/voiceToText" \
         -H "Content-Type: application/octet-stream" \
         --data-binary "@audio.wav"
    """
    try:
        audio_bytes = None
        file_format = "mp3"  # 默认格式

        # 检查请求类型
        if request.content_type and request.content_type.startswith('application/octet-stream'):
            # 处理二进制流上传
            logger.info("检测到二进制流上传")
            audio_bytes = request.get_data()
            # 从查询参数获取文件格式，如果没有则使用默认值
            file_format = request.args.get('format', 'mp3').lower()
            logger.info(f"从查询参数获取文件格式: {file_format}")
        elif 'file' in request.files:
            # 处理表单文件上传
            logger.info("检测到表单文件上传")
            file = request.files['file']
            if file.filename == '':
                return jsonify({
                    "success": False,
                    "error": "未选择文件"
                }), 400

            # 获取文件格式（扩展名）
            file_format = file.filename.split('.')[-1].lower()
            logger.info(f"从文件名获取文件格式: {file_format}")

            # 读取文件内容
            audio_bytes = file.read()
        else:
            return jsonify({
                "success": False,
                "error": "未提供音频数据，请使用表单文件上传或二进制流上传"
            }), 400

        # 验证文件格式
        if file_format not in ['mp3', 'wav', 'pcm', 'ogg']:  # 支持的格式
            return jsonify({
                "success": False,
                "error": f"不支持的文件格式: {file_format}"
            }), 400

        # 验证音频数据
        if not audio_bytes or len(audio_bytes) == 0:
            return jsonify({
                "success": False,
                "error": "音频数据为空"
            }), 400

        # 记录开始处理时间，用于计算总处理时间
        start_time = time.time()
        logger.info(f"开始处理音频文件，大小: {len(audio_bytes) / 1024:.2f}KB，格式: {file_format}")

        # 调用语音服务处理音频
        result = voice_service.voice_to_text(audio_bytes, file_format)
        
        # 计算处理时间
        process_time = time.time() - start_time
        logger.info(f"音频处理完成，耗时: {process_time:.2f}秒")
        
        # 添加处理时间到结果中
        if result.get("success", False) and "metadata" in result:
            result["metadata"]["process_time_seconds"] = process_time
            
        return jsonify(result)

    except Exception as e:
        logger.error(f"语音转文本失败: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# 导出命名空间供app.py使用
__all__ = ['voice_bp', 'ns'] 